-- Najaf Cemetery Database Initialization Script
-- This script sets up the complete database schema for the cemetery management system

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create deceased_records table (main data from government)
CREATE TABLE IF NOT EXISTS deceased_records (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(50) UNIQUE NOT NULL,
    deceased_name VARCHAR(255) NOT NULL,
    deceased_name_arabic VARCHAR(255),
    father_name VARCHAR(255),
    grandfather_name VARCHAR(255),
    death_date DATE NOT NULL,
    death_location VARCHAR(255),
    burial_date DATE NOT NULL,
    burial_location VARCHAR(255) NOT NULL,
    
    -- Cemetery location details
    section VARCHAR(50),
    row_number INTEGER,
    plot_number INTEGER,
    grave_number VARCHAR(50),
    
    -- Geospatial data
    coordinates GEOMETRY(Point, 4326),
    
    -- Additional metadata
    age_at_death INTEGER,
    cause_of_death VARCHAR(255),
    national_id VARCHAR(50),
    family_contact VARCHAR(255),
    
    -- JSON for flexible additional data
    additional_data JSONB,
    
    -- Processing metadata
    source_file VARCHAR(255),
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for deceased_records
CREATE INDEX IF NOT EXISTS idx_deceased_coordinates 
    ON deceased_records USING GIST (coordinates);

CREATE INDEX IF NOT EXISTS idx_deceased_burial_date 
    ON deceased_records (burial_date DESC);

CREATE INDEX IF NOT EXISTS idx_deceased_death_date 
    ON deceased_records (death_date DESC);

CREATE INDEX IF NOT EXISTS idx_deceased_record_id 
    ON deceased_records (record_id);

CREATE INDEX IF NOT EXISTS idx_deceased_name 
    ON deceased_records (deceased_name);

CREATE INDEX IF NOT EXISTS idx_deceased_location 
    ON deceased_records (section, row_number, plot_number);

CREATE INDEX IF NOT EXISTS idx_deceased_status 
    ON deceased_records (processing_status);

-- Create GIN index for JSONB additional_data
CREATE INDEX IF NOT EXISTS idx_deceased_additional_data 
    ON deceased_records USING GIN (additional_data);

-- Create najaf_cemetery_features table (for GeoJSON export)
CREATE TABLE IF NOT EXISTS najaf_cemetery_features (
    id SERIAL PRIMARY KEY,
    feature_id VARCHAR(255),
    geometry GEOMETRY(Geometry, 4326),
    properties JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for najaf_cemetery_features
CREATE INDEX IF NOT EXISTS idx_cemetery_features_geometry 
    ON najaf_cemetery_features USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_cemetery_features_properties 
    ON najaf_cemetery_features USING GIN (properties);

CREATE INDEX IF NOT EXISTS idx_cemetery_features_feature_id 
    ON najaf_cemetery_features (feature_id);

-- Create sync_history table
CREATE TABLE IF NOT EXISTS sync_history (
    id SERIAL PRIMARY KEY,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_type VARCHAR(50),  -- 'ftp_download', 'data_processing', 'geojson_export'
    features_count INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_sync_history_time 
    ON sync_history (sync_time DESC);

CREATE INDEX IF NOT EXISTS idx_sync_history_type 
    ON sync_history (sync_type);

-- Create file_processing_log table
CREATE TABLE IF NOT EXISTS file_processing_log (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    file_size BIGINT,
    download_time TIMESTAMP,
    extraction_time TIMESTAMP,
    processing_start_time TIMESTAMP,
    processing_end_time TIMESTAMP,
    processing_duration_seconds FLOAT,
    records_total INTEGER,
    records_processed INTEGER,
    records_failed INTEGER,
    status VARCHAR(50),  -- 'downloaded', 'extracted', 'processing', 'completed', 'failed'
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_file_processing_filename 
    ON file_processing_log (filename);

CREATE INDEX IF NOT EXISTS idx_file_processing_status 
    ON file_processing_log (status);

CREATE INDEX IF NOT EXISTS idx_file_processing_time 
    ON file_processing_log (created_at DESC);

-- Create burial_sections table (for cemetery layout)
CREATE TABLE IF NOT EXISTS burial_sections (
    id SERIAL PRIMARY KEY,
    section_code VARCHAR(50) UNIQUE NOT NULL,
    section_name VARCHAR(255),
    section_name_arabic VARCHAR(255),
    capacity INTEGER,
    occupied_count INTEGER DEFAULT 0,
    geometry GEOMETRY(Polygon, 4326),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_burial_sections_geometry 
    ON burial_sections USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_burial_sections_code 
    ON burial_sections (section_code);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_deceased_records_updated_at 
    BEFORE UPDATE ON deceased_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cemetery_features_updated_at 
    BEFORE UPDATE ON najaf_cemetery_features
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_burial_sections_updated_at 
    BEFORE UPDATE ON burial_sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for daily statistics
CREATE OR REPLACE VIEW daily_burial_stats AS
SELECT 
    burial_date,
    COUNT(*) as burials_count,
    COUNT(DISTINCT section) as sections_used,
    MIN(created_at) as first_recorded,
    MAX(created_at) as last_recorded
FROM deceased_records
WHERE processing_status = 'completed'
GROUP BY burial_date
ORDER BY burial_date DESC;

-- Create view for section occupancy
CREATE OR REPLACE VIEW section_occupancy AS
SELECT 
    s.section_code,
    s.section_name,
    s.capacity,
    COUNT(d.id) as current_occupancy,
    ROUND((COUNT(d.id)::FLOAT / NULLIF(s.capacity, 0) * 100), 2) as occupancy_percentage
FROM burial_sections s
LEFT JOIN deceased_records d ON d.section = s.section_code
WHERE d.processing_status = 'completed'
GROUP BY s.id, s.section_code, s.section_name, s.capacity
ORDER BY occupancy_percentage DESC;

-- Create view for recent burials (last 30 days)
CREATE OR REPLACE VIEW recent_burials AS
SELECT 
    record_id,
    deceased_name,
    burial_date,
    section,
    row_number,
    plot_number,
    ST_AsGeoJSON(coordinates) as coordinates_geojson,
    created_at
FROM deceased_records
WHERE burial_date >= CURRENT_DATE - INTERVAL '30 days'
    AND processing_status = 'completed'
ORDER BY burial_date DESC, created_at DESC;

-- Insert sample burial sections (Wadi al-Salam cemetery sections)
INSERT INTO burial_sections (section_code, section_name, section_name_arabic, capacity, geometry) VALUES
('A', 'Section A', 'القسم أ', 10000, ST_GeomFromText('POLYGON((44.310 32.015, 44.315 32.015, 44.315 32.020, 44.310 32.020, 44.310 32.015))', 4326)),
('B', 'Section B', 'القسم ب', 10000, ST_GeomFromText('POLYGON((44.315 32.015, 44.320 32.015, 44.320 32.020, 44.315 32.020, 44.315 32.015))', 4326)),
('C', 'Section C', 'القسم ج', 10000, ST_GeomFromText('POLYGON((44.310 32.020, 44.315 32.020, 44.315 32.025, 44.310 32.025, 44.310 32.020))', 4326))
ON CONFLICT (section_code) DO NOTHING;

-- Grant permissions to cemetery_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cemetery_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cemetery_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO cemetery_user;

-- Create database info view
CREATE OR REPLACE VIEW database_info AS
SELECT 
    'deceased_records' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM deceased_records
UNION ALL
SELECT 
    'file_processing_log' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM file_processing_log;

COMMENT ON TABLE deceased_records IS 'Main table storing deceased person records from government data';
COMMENT ON TABLE najaf_cemetery_features IS 'GeoJSON features for map visualization';
COMMENT ON TABLE sync_history IS 'History of all sync operations';
COMMENT ON TABLE file_processing_log IS 'Log of all processed ZIP files';
COMMENT ON TABLE burial_sections IS 'Cemetery section layout and capacity information';
