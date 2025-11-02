use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use log::{info, error};
use serde::{Deserialize, Serialize};
use sqlx::postgres::PgPool;
use std::sync::Arc;

mod models;
mod parser;
mod database;
mod processor;

use models::*;
use processor::DataProcessor;

#[derive(Debug, Deserialize)]
struct ProcessRequest {
    data_path: String,
    metadata: FileMetadata,
    timestamp: String,
    source: String,
}

#[derive(Debug, Serialize)]
struct ProcessResponse {
    success: bool,
    records_processed: i32,
    records_failed: i32,
    processing_time_seconds: f64,
    geojson_features_created: i32,
    errors: Vec<ProcessingError>,
}

#[derive(Debug, Serialize)]
struct ProcessingError {
    record_id: Option<String>,
    error: String,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    success: bool,
    error: String,
    details: Option<String>,
}

#[derive(Clone)]
struct AppState {
    db_pool: Arc<PgPool>,
}

// Health check endpoint
async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "najaf-cemetery-processor",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

// Main processing endpoint
async fn process_data(
    req: web::Json<ProcessRequest>,
    state: web::Data<AppState>,
) -> impl Responder {
    info!("Received processing request for: {}", req.data_path);
    info!("Source file: {}", req.metadata.filename);
    
    let start_time = std::time::Instant::now();
    
    // Create processor instance
    let processor = DataProcessor::new(state.db_pool.clone());
    
    // Process the data
    match processor.process_directory(&req.data_path, &req.metadata).await {
        Ok(result) => {
            let duration = start_time.elapsed().as_secs_f64();
            
            info!(
                "Processing completed: {} records processed, {} failed in {:.2}s",
                result.records_processed, result.records_failed, duration
            );
            
            HttpResponse::Ok().json(ProcessResponse {
                success: true,
                records_processed: result.records_processed,
                records_failed: result.records_failed,
                processing_time_seconds: duration,
                geojson_features_created: result.geojson_features_created,
                errors: result.errors.into_iter().map(|e| ProcessingError {
                    record_id: e.record_id,
                    error: e.message,
                }).collect(),
            })
        }
        Err(e) => {
            error!("Processing failed: {}", e);
            
            HttpResponse::InternalServerError().json(ErrorResponse {
                success: false,
                error: "Processing failed".to_string(),
                details: Some(e.to_string()),
            })
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize logger
    env_logger::init();
    
    // Load environment variables
    dotenv::dotenv().ok();
    
    // Get configuration from environment
    let database_url = std::env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
    let server_host = std::env::var("SERVER_HOST")
        .unwrap_or_else(|_| "0.0.0.0".to_string());
    let server_port = std::env::var("SERVER_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse::<u16>()
        .expect("SERVER_PORT must be a valid port number");
    
    info!("Connecting to database...");
    
    // Create database connection pool
    let db_pool = PgPool::connect(&database_url)
        .await
        .expect("Failed to connect to database");
    
    info!("Database connection established");
    
    // Create app state
    let app_state = AppState {
        db_pool: Arc::new(db_pool),
    };
    
    info!("Starting server at {}:{}", server_host, server_port);
    
    // Start HTTP server
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(app_state.clone()))
            .route("/health", web::get().to(health_check))
            .route("/api/process", web::post().to(process_data))
    })
    .bind((server_host, server_port))?
    .run()
    .await
}
