use crate::models::{DeceasedRecord, ErrorDetails};
use chrono::NaiveDate;
use log::{info, warn, error};
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

pub struct DataParser;

impl DataParser {
    pub fn parse_csv_file(file_path: &Path) -> Result<Vec<DeceasedRecord>, anyhow::Error> {
        info!("Parsing CSV file: {:?}", file_path);
        
        let file = File::open(file_path)?;
        let mut reader = csv::Reader::from_reader(BufReader::new(file));
        
        let mut records = Vec::new();
        let mut line_number = 1; // Header is line 0
        
        for result in reader.deserialize() {
            line_number += 1;
            
            match result {
                Ok(record) => {
                    records.push(Self::parse_csv_record(record)?);
                }
                Err(e) => {
                    warn!("Error parsing CSV line {}: {}", line_number, e);
                }
            }
        }
        
        info!("Successfully parsed {} records from CSV", records.len());
        Ok(records)
    }
    
    fn parse_csv_record(record: csv::StringRecord) -> Result<DeceasedRecord, anyhow::Error> {
        // This is a flexible parser - adjust based on your actual CSV format
        // Expected columns: record_id, deceased_name, death_date, burial_date, 
        //                   burial_location, latitude, longitude, section, row, plot
        
        Ok(DeceasedRecord {
            record_id: record.get(0).unwrap_or("").to_string(),
            deceased_name: record.get(1).unwrap_or("").to_string(),
            deceased_name_arabic: record.get(2).map(|s| s.to_string()),
            father_name: None,
            grandfather_name: None,
            death_date: NaiveDate::parse_from_str(
                record.get(3).unwrap_or(""),
                "%Y-%m-%d"
            )?,
            death_location: None,
            burial_date: NaiveDate::parse_from_str(
                record.get(4).unwrap_or(""),
                "%Y-%m-%d"
            )?,
            burial_location: record.get(5).unwrap_or("").to_string(),
            section: record.get(8).map(|s| s.to_string()),
            row_number: record.get(9).and_then(|s| s.parse::<i32>().ok()),
            plot_number: record.get(10).and_then(|s| s.parse::<i32>().ok()),
            grave_number: None,
            latitude: record.get(6).and_then(|s| s.parse::<f64>().ok()),
            longitude: record.get(7).and_then(|s| s.parse::<f64>().ok()),
            age_at_death: None,
            cause_of_death: None,
            national_id: None,
            family_contact: None,
            additional_data: None,
        })
    }
    
    pub fn parse_json_file(file_path: &Path) -> Result<Vec<DeceasedRecord>, anyhow::Error> {
        info!("Parsing JSON file: {:?}", file_path);
        
        let file = File::open(file_path)?;
        let reader = BufReader::new(file);
        
        #[derive(serde::Deserialize)]
        struct JsonData {
            records: Vec<JsonRecord>,
        }
        
        #[derive(serde::Deserialize)]
        struct JsonRecord {
            record_id: String,
            deceased_name: String,
            deceased_name_arabic: Option<String>,
            death_date: String,
            burial_date: String,
            burial_location: String,
            coordinates: Option<JsonCoordinates>,
            location: Option<JsonLocation>,
        }
        
        #[derive(serde::Deserialize)]
        struct JsonCoordinates {
            latitude: f64,
            longitude: f64,
        }
        
        #[derive(serde::Deserialize)]
        struct JsonLocation {
            section: Option<String>,
            row: Option<i32>,
            plot: Option<i32>,
        }
        
        let data: JsonData = serde_json::from_reader(reader)?;
        
        let mut records = Vec::new();
        
        for json_record in data.records {
            let record = DeceasedRecord {
                record_id: json_record.record_id,
                deceased_name: json_record.deceased_name,
                deceased_name_arabic: json_record.deceased_name_arabic,
                father_name: None,
                grandfather_name: None,
                death_date: NaiveDate::parse_from_str(&json_record.death_date, "%Y-%m-%d")?,
                death_location: None,
                burial_date: NaiveDate::parse_from_str(&json_record.burial_date, "%Y-%m-%d")?,
                burial_location: json_record.burial_location,
                section: json_record.location.as_ref().and_then(|l| l.section.clone()),
                row_number: json_record.location.as_ref().and_then(|l| l.row),
                plot_number: json_record.location.as_ref().and_then(|l| l.plot),
                grave_number: None,
                latitude: json_record.coordinates.as_ref().map(|c| c.latitude),
                longitude: json_record.coordinates.as_ref().map(|c| c.longitude),
                age_at_death: None,
                cause_of_death: None,
                national_id: None,
                family_contact: None,
                additional_data: None,
            };
            
            records.push(record);
        }
        
        info!("Successfully parsed {} records from JSON", records.len());
        Ok(records)
    }
    
    pub fn detect_and_parse(file_path: &Path) -> Result<Vec<DeceasedRecord>, anyhow::Error> {
        let extension = file_path.extension()
            .and_then(|s| s.to_str())
            .map(|s| s.to_lowercase());
        
        match extension.as_deref() {
            Some("csv") => Self::parse_csv_file(file_path),
            Some("json") => Self::parse_json_file(file_path),
            Some(ext) => {
                error!("Unsupported file format: {}", ext);
                Err(anyhow::anyhow!("Unsupported file format: {}", ext))
            }
            None => {
                error!("No file extension found");
                Err(anyhow::anyhow!("No file extension found"))
            }
        }
    }
}
