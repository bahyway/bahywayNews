use crate::models::DeceasedRecord;
use sqlx::{PgPool, Postgres, QueryBuilder};
use log::{info, error};

pub struct Database {
    pool: PgPool,
}

impl Database {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
    
    pub async fn insert_deceased_record(
        &self,
        record: &DeceasedRecord,
        source_file: &str,
    ) -> Result<i64, sqlx::Error> {
        let coordinates_wkt = if let (Some(lat), Some(lon)) = (record.latitude, record.longitude) {
            Some(format!("POINT({} {})", lon, lat))
        } else {
            None
        };
        
        let result = sqlx::query!(
            r#"
            INSERT INTO deceased_records (
                record_id, deceased_name, deceased_name_arabic,
                father_name, grandfather_name,
                death_date, death_location, burial_date, burial_location,
                section, row_number, plot_number, grave_number,
                coordinates,
                age_at_death, cause_of_death, national_id, family_contact,
                additional_data, source_file, processing_status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                ST_GeomFromText($14, 4326),
                $15, $16, $17, $18, $19, $20, $21
            )
            ON CONFLICT (record_id) DO UPDATE SET
                deceased_name = EXCLUDED.deceased_name,
                burial_date = EXCLUDED.burial_date,
                coordinates = EXCLUDED.coordinates,
                updated_at = CURRENT_TIMESTAMP,
                processing_status = EXCLUDED.processing_status
            RETURNING id
            "#,
            record.record_id,
            record.deceased_name,
            record.deceased_name_arabic,
            record.father_name,
            record.grandfather_name,
            record.death_date,
            record.death_location,
            record.burial_date,
            record.burial_location,
            record.section,
            record.row_number,
            record.plot_number,
            record.grave_number,
            coordinates_wkt,
            record.age_at_death,
            record.cause_of_death,
            record.national_id,
            record.family_contact,
            record.additional_data,
            source_file,
            "completed"
        )
        .fetch_one(&self.pool)
        .await?;
        
        Ok(result.id)
    }
    
    pub async fn insert_batch(
        &self,
        records: &[DeceasedRecord],
        source_file: &str,
    ) -> Result<usize, sqlx::Error> {
        let mut inserted = 0;
        
        for record in records {
            match self.insert_deceased_record(record, source_file).await {
                Ok(_) => inserted += 1,
                Err(e) => {
                    error!("Failed to insert record {}: {}", record.record_id, e);
                }
            }
        }
        
        info!("Inserted {} records into database", inserted);
        Ok(inserted)
    }
    
    pub async fn create_geojson_features(&self) -> Result<i32, sqlx::Error> {
        // Clear existing features
        sqlx::query!("DELETE FROM najaf_cemetery_features")
            .execute(&self.pool)
            .await?;
        
        // Insert new features from deceased_records
        let result = sqlx::query!(
            r#"
            INSERT INTO najaf_cemetery_features (feature_id, geometry, properties)
            SELECT 
                record_id as feature_id,
                coordinates as geometry,
                jsonb_build_object(
                    'record_id', record_id,
                    'name', deceased_name,
                    'burial_date', burial_date::text,
                    'burial_location', burial_location,
                    'section', section,
                    'row', row_number,
                    'plot', plot_number
                ) as properties
            FROM deceased_records
            WHERE coordinates IS NOT NULL
                AND processing_status = 'completed'
            "#
        )
        .execute(&self.pool)
        .await?;
        
        Ok(result.rows_affected() as i32)
    }
    
    pub async fn log_file_processing(
        &self,
        filename: &str,
        file_hash: &str,
        file_size: i64,
        records_total: i32,
        records_processed: i32,
        records_failed: i32,
        status: &str,
        error_message: Option<&str>,
    ) -> Result<(), sqlx::Error> {
        sqlx::query!(
            r#"
            INSERT INTO file_processing_log (
                filename, file_hash, file_size,
                records_total, records_processed, records_failed,
                status, error_message, processing_end_time
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
            "#,
            filename,
            file_hash,
            file_size,
            records_total,
            records_processed,
            records_failed,
            status,
            error_message
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
}
