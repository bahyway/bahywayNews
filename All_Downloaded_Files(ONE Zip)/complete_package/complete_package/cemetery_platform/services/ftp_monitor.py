"""
Najaf Cemetery Data Pipeline - FTP Monitor Module
Monitors FTP/SFTP location for daily zip files containing deceased records
Downloads, extracts, and triggers Rust microservice for processing
"""

import os
import ftplib
import paramiko
import zipfile
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import time
import subprocess
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ftp_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FTPMonitor:
    """Monitors FTP/SFTP server for new zip files from government establishment"""
    
    def __init__(self, config: Dict):
        """
        Initialize FTP Monitor
        
        Args:
            config: Dictionary containing FTP/SFTP configuration
        """
        self.config = config
        self.protocol = config.get('protocol', 'sftp').lower()  # 'ftp' or 'sftp'
        self.host = config['host']
        self.port = config.get('port', 22 if self.protocol == 'sftp' else 21)
        self.username = config['username']
        self.password = config['password']
        self.remote_path = config.get('remote_path', '/')
        
        # Local paths
        self.download_dir = Path(config.get('download_dir', './downloads'))
        self.extract_dir = Path(config.get('extract_dir', './extracted'))
        self.archive_dir = Path(config.get('archive_dir', './archive'))
        self.processed_log = Path(config.get('processed_log', './processed_files.json'))
        
        # Create directories
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Rust microservice configuration
        self.rust_service_url = config.get('rust_service_url', 'http://localhost:8080/process')
        self.rust_service_enabled = config.get('rust_service_enabled', True)
        
        # Load processed files history
        self.processed_files = self._load_processed_files()
    
    def _load_processed_files(self) -> Dict:
        """Load the history of processed files"""
        if self.processed_log.exists():
            with open(self.processed_log, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_processed_files(self):
        """Save the history of processed files"""
        with open(self.processed_log, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def connect_sftp(self) -> paramiko.SFTPClient:
        """Establish SFTP connection"""
        try:
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            logger.info(f"Connected to SFTP server: {self.host}:{self.port}")
            return sftp
        except Exception as e:
            logger.error(f"SFTP connection failed: {e}")
            raise
    
    def connect_ftp(self) -> ftplib.FTP:
        """Establish FTP connection"""
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.host, self.port)
            ftp.login(self.username, self.password)
            ftp.cwd(self.remote_path)
            logger.info(f"Connected to FTP server: {self.host}:{self.port}")
            return ftp
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            raise
    
    def list_remote_files_sftp(self, sftp: paramiko.SFTPClient) -> List[Dict]:
        """List zip files on SFTP server"""
        try:
            files = []
            for attr in sftp.listdir_attr(self.remote_path):
                if attr.filename.endswith('.zip'):
                    files.append({
                        'filename': attr.filename,
                        'size': attr.st_size,
                        'mtime': attr.st_mtime,
                        'remote_path': f"{self.remote_path}/{attr.filename}"
                    })
            return files
        except Exception as e:
            logger.error(f"Error listing SFTP files: {e}")
            return []
    
    def list_remote_files_ftp(self, ftp: ftplib.FTP) -> List[Dict]:
        """List zip files on FTP server"""
        try:
            files = []
            file_list = []
            ftp.retrlines('LIST', file_list.append)
            
            for line in file_list:
                parts = line.split()
                if len(parts) >= 9 and parts[-1].endswith('.zip'):
                    filename = parts[-1]
                    size = int(parts[4])
                    files.append({
                        'filename': filename,
                        'size': size,
                        'remote_path': f"{self.remote_path}/{filename}"
                    })
            return files
        except Exception as e:
            logger.error(f"Error listing FTP files: {e}")
            return []
    
    def download_file_sftp(self, sftp: paramiko.SFTPClient, remote_file: Dict) -> Optional[Path]:
        """Download file via SFTP"""
        try:
            local_path = self.download_dir / remote_file['filename']
            
            logger.info(f"Downloading {remote_file['filename']} ({remote_file['size']} bytes)")
            sftp.get(remote_file['remote_path'], str(local_path))
            
            logger.info(f"Downloaded to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading file via SFTP: {e}")
            return None
    
    def download_file_ftp(self, ftp: ftplib.FTP, remote_file: Dict) -> Optional[Path]:
        """Download file via FTP"""
        try:
            local_path = self.download_dir / remote_file['filename']
            
            logger.info(f"Downloading {remote_file['filename']} ({remote_file['size']} bytes)")
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_file["filename"]}', f.write)
            
            logger.info(f"Downloaded to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading file via FTP: {e}")
            return None
    
    def extract_zip(self, zip_path: Path) -> Optional[Path]:
        """Extract zip file to extraction directory"""
        try:
            # Create extraction subdirectory with timestamp
            extract_subdir = self.extract_dir / f"{zip_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            extract_subdir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Extracting {zip_path.name} to {extract_subdir}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_subdir)
                file_list = zip_ref.namelist()
            
            logger.info(f"Extracted {len(file_list)} files: {', '.join(file_list[:5])}{'...' if len(file_list) > 5 else ''}")
            return extract_subdir
        except Exception as e:
            logger.error(f"Error extracting zip file: {e}")
            return None
    
    def trigger_rust_microservice(self, extracted_path: Path, metadata: Dict) -> bool:
        """
        Trigger Rust microservice to process the extracted data
        
        Args:
            extracted_path: Path to extracted files
            metadata: Metadata about the processing job
            
        Returns:
            True if successful, False otherwise
        """
        if not self.rust_service_enabled:
            logger.info("Rust microservice is disabled, skipping trigger")
            return True
        
        try:
            payload = {
                'data_path': str(extracted_path.absolute()),
                'metadata': metadata,
                'timestamp': datetime.now().isoformat(),
                'source': 'ftp_monitor'
            }
            
            logger.info(f"Triggering Rust microservice at {self.rust_service_url}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.rust_service_url,
                json=payload,
                timeout=300  # 5 minutes timeout for processing
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Rust microservice response: {result}")
                return True
            else:
                logger.error(f"Rust microservice returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Rust microservice: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error triggering Rust microservice: {e}")
            return False
    
    def archive_file(self, file_path: Path):
        """Move processed file to archive directory"""
        try:
            archive_path = self.archive_dir / file_path.name
            file_path.rename(archive_path)
            logger.info(f"Archived {file_path.name} to {archive_path}")
        except Exception as e:
            logger.error(f"Error archiving file: {e}")
    
    def process_file(self, remote_file: Dict, connection) -> bool:
        """
        Complete processing workflow for a single file
        
        Args:
            remote_file: Dictionary with file information
            connection: FTP or SFTP connection object
            
        Returns:
            True if processing succeeded, False otherwise
        """
        filename = remote_file['filename']
        
        # Check if already processed
        if filename in self.processed_files:
            logger.info(f"File {filename} already processed, skipping")
            return True
        
        # Download file
        if self.protocol == 'sftp':
            local_path = self.download_file_sftp(connection, remote_file)
        else:
            local_path = self.download_file_ftp(connection, remote_file)
        
        if not local_path:
            return False
        
        # Calculate file hash for verification
        file_hash = self._get_file_hash(local_path)
        
        # Extract zip file
        extracted_path = self.extract_zip(local_path)
        if not extracted_path:
            return False
        
        # Prepare metadata
        metadata = {
            'filename': filename,
            'file_hash': file_hash,
            'size': remote_file['size'],
            'download_time': datetime.now().isoformat(),
            'extracted_path': str(extracted_path)
        }
        
        # Trigger Rust microservice
        rust_success = self.trigger_rust_microservice(extracted_path, metadata)
        
        if rust_success:
            # Mark as processed
            self.processed_files[filename] = {
                'processed_at': datetime.now().isoformat(),
                'file_hash': file_hash,
                'metadata': metadata,
                'status': 'success'
            }
            self._save_processed_files()
            
            # Archive the zip file
            self.archive_file(local_path)
            
            logger.info(f"Successfully processed {filename}")
            return True
        else:
            # Mark as failed
            self.processed_files[filename] = {
                'processed_at': datetime.now().isoformat(),
                'file_hash': file_hash,
                'metadata': metadata,
                'status': 'failed'
            }
            self._save_processed_files()
            
            logger.error(f"Failed to process {filename}")
            return False
    
    def scan_and_process(self) -> Dict:
        """
        Scan FTP/SFTP server and process new files
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'scan_time': datetime.now().isoformat(),
            'files_found': 0,
            'files_processed': 0,
            'files_failed': 0,
            'files_skipped': 0
        }
        
        try:
            # Connect to server
            if self.protocol == 'sftp':
                connection = self.connect_sftp()
                remote_files = self.list_remote_files_sftp(connection)
            else:
                connection = self.connect_ftp()
                remote_files = self.list_remote_files_ftp(connection)
            
            stats['files_found'] = len(remote_files)
            logger.info(f"Found {len(remote_files)} zip files on remote server")
            
            # Process each file
            for remote_file in remote_files:
                if remote_file['filename'] in self.processed_files:
                    stats['files_skipped'] += 1
                    continue
                
                success = self.process_file(remote_file, connection)
                
                if success:
                    stats['files_processed'] += 1
                else:
                    stats['files_failed'] += 1
            
            # Close connection
            if self.protocol == 'sftp':
                connection.close()
            else:
                connection.quit()
            
            logger.info(f"Scan completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during scan and process: {e}")
            stats['error'] = str(e)
            return stats
    
    def continuous_monitor(self, interval_minutes: int = 30):
        """
        Continuously monitor FTP/SFTP server for new files
        
        Args:
            interval_minutes: Time between scans in minutes
        """
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                logger.info("=" * 50)
                logger.info("Starting new scan cycle")
                logger.info("=" * 50)
                
                stats = self.scan_and_process()
                
                logger.info(f"Next scan in {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                logger.info(f"Retrying in {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)


def main():
    """Main function"""
    
    # Configuration
    config = {
        'protocol': 'sftp',  # 'sftp' or 'ftp'
        'host': 'ftp.government-establishment.iq',
        'port': 22,  # 22 for SFTP, 21 for FTP
        'username': 'najaf_cemetery',
        'password': 'your_secure_password',
        'remote_path': '/deceased_records',
        
        # Local directories
        'download_dir': './data/downloads',
        'extract_dir': './data/extracted',
        'archive_dir': './data/archive',
        'processed_log': './data/processed_files.json',
        
        # Rust microservice
        'rust_service_url': 'http://localhost:8080/api/process',
        'rust_service_enabled': True
    }
    
    # Initialize monitor
    monitor = FTPMonitor(config)
    
    # Run continuous monitoring (scans every 30 minutes)
    monitor.continuous_monitor(interval_minutes=30)


if __name__ == "__main__":
    main()
