use serde::{Deserialize, Serialize};
use chrono::{NaiveDate, DateTime, Utc};
use sqlx::FromRow;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct FileMetadata {
    pub filename: String,
    pub file_hash: String,
    pub size: i64,
    pub download_time: String,
    pub extracted_path: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct DeceasedRecord {
    pub record_id: String,
    pub deceased_name: String,
    pub deceased_name_arabic: Option<String>,
    pub father_name: Option<String>,
    pub grandfather_name: Option<String>,
    pub death_date: NaiveDate,
    pub death_location: Option<String>,
    pub burial_date: NaiveDate,
    pub burial_location: String,
    
    // Cemetery location
    pub section: Option<String>,
    pub row_number: Option<i32>,
    pub plot_number: Option<i32>,
    pub grave_number: Option<String>,
    
    // Coordinates
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
    
    // Additional info
    pub age_at_death: Option<i32>,
    pub cause_of_death: Option<String>,
    pub national_id: Option<String>,
    pub family_contact: Option<String>,
    
    // Metadata
    pub additional_data: Option<serde_json::Value>,
}

#[derive(Debug, FromRow)]
pub struct DbDeceasedRecord {
    pub id: i32,
    pub record_id: String,
    pub deceased_name: String,
    pub burial_date: NaiveDate,
    pub section: Option<String>,
    pub row_number: Option<i32>,
    pub plot_number: Option<i32>,
    pub processing_status: String,
}

#[derive(Debug, Serialize)]
pub struct GeoJsonFeature {
    #[serde(rename = "type")]
    pub feature_type: String,
    pub geometry: GeoJsonGeometry,
    pub properties: serde_json::Value,
}

#[derive(Debug, Serialize)]
pub struct GeoJsonGeometry {
    #[serde(rename = "type")]
    pub geometry_type: String,
    pub coordinates: Vec<f64>,
}

#[derive(Debug)]
pub struct ProcessingResult {
    pub records_processed: i32,
    pub records_failed: i32,
    pub geojson_features_created: i32,
    pub errors: Vec<ErrorDetails>,
}

#[derive(Debug, Clone)]
pub struct ErrorDetails {
    pub record_id: Option<String>,
    pub message: String,
}

impl DeceasedRecord {
    pub fn validate(&self) -> Result<(), String> {
        // Validate required fields
        if self.record_id.is_empty() {
            return Err("record_id is required".to_string());
        }
        
        if self.deceased_name.is_empty() {
            return Err("deceased_name is required".to_string());
        }
        
        if self.burial_location.is_empty() {
            return Err("burial_location is required".to_string());
        }
        
        // Validate dates
        if self.burial_date < self.death_date {
            return Err("burial_date cannot be before death_date".to_string());
        }
        
        // Validate coordinates if present
        if let (Some(lat), Some(lon)) = (self.latitude, self.longitude) {
            if lat < -90.0 || lat > 90.0 {
                return Err("Invalid latitude".to_string());
            }
            if lon < -180.0 || lon > 180.0 {
                return Err("Invalid longitude".to_string());
            }
        }
        
        Ok(())
    }
    
    pub fn has_coordinates(&self) -> bool {
        self.latitude.is_some() && self.longitude.is_some()
    }
    
    pub fn to_geojson_feature(&self) -> Option<GeoJsonFeature> {
        if !self.has_coordinates() {
            return None;
        }
        
        let mut properties = serde_json::Map::new();
        properties.insert("record_id".to_string(), serde_json::json!(self.record_id));
        properties.insert("name".to_string(), serde_json::json!(self.deceased_name));
        properties.insert("burial_date".to_string(), serde_json::json!(self.burial_date.to_string()));
        properties.insert("burial_location".to_string(), serde_json::json!(self.burial_location));
        
        if let Some(section) = &self.section {
            properties.insert("section".to_string(), serde_json::json!(section));
        }
        if let Some(row) = self.row_number {
            properties.insert("row".to_string(), serde_json::json!(row));
        }
        if let Some(plot) = self.plot_number {
            properties.insert("plot".to_string(), serde_json::json!(plot));
        }
        
        Some(GeoJsonFeature {
            feature_type: "Feature".to_string(),
            geometry: GeoJsonGeometry {
                geometry_type: "Point".to_string(),
                coordinates: vec![self.longitude.unwrap(), self.latitude.unwrap()],
            },
            properties: serde_json::Value::Object(properties),
        })
    }
}
