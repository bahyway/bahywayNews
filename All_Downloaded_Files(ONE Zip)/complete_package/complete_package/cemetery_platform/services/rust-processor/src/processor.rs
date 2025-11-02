use crate::models::{DeceasedRecord, ErrorDetails, FileMetadata, ProcessingResult};
use crate::parser::DataParser;
use crate::database::Database;
use sqlx::PgPool;
use log::{info, warn, error};
use std::path::Path;
use std::sync::Arc;

pub struct DataProcessor {
    db: Database,
}

impl DataProcessor {
    pub fn new(pool: Arc<PgPool>) -> Self {
        Self {
            db: Database::new((*pool).clone()),
        }
    }
    
    pub async fn process_directory(
        &self,
        directory_path: &str,
        metadata: &FileMetadata,
    ) -> Result<ProcessingResult, anyhow::Error> {
        info!("Processing directory: {}", directory_path);
        
        let dir = Path::new(directory_path);
        
        if !dir.exists() || !dir.is_dir() {
            return Err(anyhow::anyhow!("Directory does not exist or is not a directory"));
        }
        
        let mut all_records = Vec::new();
        let mut errors = Vec::new();
        
        // Find and parse all CSV and JSON files in the directory
        let entries = std::fs::read_dir(dir)?;
        
        for entry in entries {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_file() {
                info!("Processing file: {:?}", path);
                
                match DataParser::detect_and_parse(&path) {
                    Ok(records) => {
                        info!("Parsed {} records from {:?}", records.len(), path);
                        all_records.extend(records);
                    }
                    Err(e) => {
                        warn!("Failed to parse file {:?}: {}", path, e);
                        errors.push(ErrorDetails {
                            record_id: None,
                            message: format!("Failed to parse file {:?}: {}", path, e),
                        });
                    }
                }
            }
        }
        
        info!("Total records parsed: {}", all_records.len());
        
        // Validate and filter records
        let mut valid_records = Vec::new();
        
        for record in all_records {
            match record.validate() {
                Ok(()) => {
                    valid_records.push(record);
                }
                Err(e) => {
                    warn!("Validation failed for record {}: {}", record.record_id, e);
                    errors.push(ErrorDetails {
                        record_id: Some(record.record_id.clone()),
                        message: e,
                    });
                }
            }
        }
        
        info!("Valid records: {}", valid_records.len());
        info!("Invalid records: {}", errors.len());
        
        // Insert records into database
        let inserted = self.db.insert_batch(&valid_records, &metadata.filename).await?;
        
        // Create GeoJSON features
        let geojson_count = self.db.create_geojson_features().await?;
        
        // Log the processing
        self.db.log_file_processing(
            &metadata.filename,
            &metadata.file_hash,
            metadata.size,
            valid_records.len() as i32 + errors.len() as i32,
            inserted as i32,
            errors.len() as i32,
            "completed",
            None,
        ).await?;
        
        Ok(ProcessingResult {
            records_processed: inserted as i32,
            records_failed: errors.len() as i32,
            geojson_features_created: geojson_count,
            errors,
        })
    }
    
    pub async fn process_single_file(
        &self,
        file_path: &str,
        metadata: &FileMetadata,
    ) -> Result<ProcessingResult, anyhow::Error> {
        info!("Processing single file: {}", file_path);
        
        let path = Path::new(file_path);
        
        if !path.exists() || !path.is_file() {
            return Err(anyhow::anyhow!("File does not exist or is not a file"));
        }
        
        // Parse the file
        let records = DataParser::detect_and_parse(path)?;
        
        info!("Parsed {} records", records.len());
        
        // Validate records
        let mut valid_records = Vec::new();
        let mut errors = Vec::new();
        
        for record in records {
            match record.validate() {
                Ok(()) => {
                    valid_records.push(record);
                }
                Err(e) => {
                    warn!("Validation failed for record {}: {}", record.record_id, e);
                    errors.push(ErrorDetails {
                        record_id: Some(record.record_id.clone()),
                        message: e,
                    });
                }
            }
        }
        
        // Insert into database
        let inserted = self.db.insert_batch(&valid_records, &metadata.filename).await?;
        
        // Create GeoJSON features
        let geojson_count = self.db.create_geojson_features().await?;
        
        // Log the processing
        self.db.log_file_processing(
            &metadata.filename,
            &metadata.file_hash,
            metadata.size,
            valid_records.len() as i32 + errors.len() as i32,
            inserted as i32,
            errors.len() as i32,
            "completed",
            None,
        ).await?;
        
        Ok(ProcessingResult {
            records_processed: inserted as i32,
            records_failed: errors.len() as i32,
            geojson_features_created: geojson_count,
            errors,
        })
    }
}
