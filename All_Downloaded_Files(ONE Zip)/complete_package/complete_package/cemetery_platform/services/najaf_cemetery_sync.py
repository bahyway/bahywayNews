"""
Najaf Cemetery GeoJSON Sync Module
Downloads GeoJSON data and stores it in PostgreSQL/PostGIS
"""

import requests
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('najaf_cemetery_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NajafCemeterySync:
    """Handles downloading and syncing Najaf cemetery GeoJSON data to PostgreSQL"""
    
    def __init__(self, geojson_url: str, db_config: Dict[str, str]):
        """
        Initialize the sync module
        
        Args:
            geojson_url: URL to the GeoJSON file on geojson.io
            db_config: Dictionary containing PostgreSQL connection parameters
                      (host, database, user, password, port)
        """
        self.geojson_url = geojson_url
        self.db_config = db_config
        self.table_name = 'najaf_cemetery_features'
        
    def download_geojson(self) -> Optional[Dict]:
        """
        Download GeoJSON data from the specified URL
        
        Returns:
            Dictionary containing GeoJSON data or None if failed
        """
        try:
            logger.info(f"Downloading GeoJSON from {self.geojson_url}")
            response = requests.get(self.geojson_url, timeout=30)
            response.raise_for_status()
            
            geojson_data = response.json()
            logger.info(f"Successfully downloaded GeoJSON with {len(geojson_data.get('features', []))} features")
            return geojson_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading GeoJSON: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing GeoJSON: {e}")
            return None
    
    def create_database_schema(self):
        """Create the necessary database tables with PostGIS support"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Enable PostGIS extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            logger.info("PostGIS extension enabled")
            
            # Create table for storing GeoJSON features
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                feature_id VARCHAR(255),
                geometry GEOMETRY(Geometry, 4326),
                properties JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_geometry 
                ON {self.table_name} USING GIST (geometry);
            
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_properties 
                ON {self.table_name} USING GIN (properties);
            
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_feature_id 
                ON {self.table_name} (feature_id);
            """
            
            cursor.execute(create_table_query)
            logger.info(f"Table {self.table_name} created successfully")
            
            # Create sync history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id SERIAL PRIMARY KEY,
                sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                features_count INTEGER,
                status VARCHAR(50),
                error_message TEXT
            );
            """)
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            logger.error(f"Database error during schema creation: {e}")
            raise
    
    def save_to_database(self, geojson_data: Dict) -> bool:
        """
        Save GeoJSON features to PostgreSQL database
        
        Args:
            geojson_data: Dictionary containing GeoJSON data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            features = geojson_data.get('features', [])
            
            if not features:
                logger.warning("No features found in GeoJSON data")
                return False
            
            # Clear existing data (or you can implement upsert logic)
            cursor.execute(f"TRUNCATE TABLE {self.table_name};")
            logger.info(f"Cleared existing data from {self.table_name}")
            
            # Prepare data for insertion
            insert_query = f"""
            INSERT INTO {self.table_name} (feature_id, geometry, properties)
            VALUES %s
            """
            
            values = []
            for feature in features:
                feature_id = feature.get('id', feature.get('properties', {}).get('id', None))
                geometry = json.dumps(feature.get('geometry'))
                properties = json.dumps(feature.get('properties', {}))
                
                values.append((
                    feature_id,
                    f"ST_GeomFromGeoJSON('{geometry}')",
                    properties
                ))
            
            # Use execute_values for efficient bulk insert
            execute_values(
                cursor,
                f"""
                INSERT INTO {self.table_name} (feature_id, geometry, properties)
                VALUES %s
                """,
                [(v[0], v[2]) for v in values],
                template="(%s, ST_GeomFromGeoJSON(%s), %s)",
                page_size=100
            )
            
            # Alternative approach using individual inserts for complex geometries
            for feature in features:
                feature_id = feature.get('id', feature.get('properties', {}).get('id', None))
                geometry_json = json.dumps(feature.get('geometry'))
                properties_json = json.dumps(feature.get('properties', {}))
                
                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name} (feature_id, geometry, properties)
                    VALUES (%s, ST_GeomFromGeoJSON(%s), %s)
                    """,
                    (feature_id, geometry_json, properties_json)
                )
            
            # Log sync history
            cursor.execute(
                """
                INSERT INTO sync_history (features_count, status)
                VALUES (%s, %s)
                """,
                (len(features), 'success')
            )
            
            conn.commit()
            logger.info(f"Successfully saved {len(features)} features to database")
            
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Database error during save: {e}")
            
            # Log failed sync
            try:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO sync_history (features_count, status, error_message)
                    VALUES (%s, %s, %s)
                    """,
                    (0, 'failed', str(e))
                )
                conn.commit()
                cursor.close()
                conn.close()
            except:
                pass
            
            return False
    
    def sync(self) -> bool:
        """
        Perform a complete sync: download and save to database
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting sync process")
        
        # Download GeoJSON data
        geojson_data = self.download_geojson()
        if not geojson_data:
            return False
        
        # Save to database
        success = self.save_to_database(geojson_data)
        
        if success:
            logger.info("Sync completed successfully")
        else:
            logger.error("Sync failed")
        
        return success


def main():
    """Main function to run the sync"""
    
    # Configuration
    GEOJSON_URL = "https://api.geojson.io/features/your-geojson-id"  # Replace with actual URL
    
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'najaf_cemetery',
        'user': 'postgres',
        'password': 'your_password',
        'port': 5432
    }
    
    # Initialize and run sync
    syncer = NajafCemeterySync(GEOJSON_URL, DB_CONFIG)
    
    # Create database schema (run once or when needed)
    syncer.create_database_schema()
    
    # Perform sync
    syncer.sync()


if __name__ == "__main__":
    main()
