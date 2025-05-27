// theater_api.rs - REST API wrapper for web_theater module
// This creates a small HTTP server that Python can call instead of using subprocess

use actix_web::{web, App, HttpResponse, HttpServer, Result};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

// Import from your web_theater module
use crate::web_theater::{
    DataTheater, EncryptionLevel, EncryptionResult, FuneralType,
    encryption_race, RaceParticipant,
};

#[derive(Deserialize)]
struct EncryptRequest {
    user_id: u64,
    data: String,
    level: String,
}

#[derive(Deserialize)]
struct FuneralRequest {
    user_id: u64,
    data_ids: Vec<String>,
    funeral_type: String,
}

#[derive(Deserialize)]
struct RaceRequest {
    participants: Vec<RaceParticipant>,
    data_size: usize,
}

#[derive(Serialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

struct AppState {
    theater: Arc<Mutex<DataTheater>>,
}

async fn encrypt_handler(
    data: web::Json<EncryptRequest>,
    state: web::Data<AppState>,
) -> Result<HttpResponse> {
    let level = match data.level.as_str() {
        "basic" => EncryptionLevel::Basic,
        "premium" => EncryptionLevel::Premium,
        "paranoid" => EncryptionLevel::Paranoid,
        "tinfoil" => EncryptionLevel::Tinfoil,
        "quantum" => EncryptionLevel::Quantum,
        "alien" => EncryptionLevel::Alien,
        "eldritch" => EncryptionLevel::Eldritch,
        _ => EncryptionLevel::Basic,
    };

    let mut theater = state.theater.lock().await;
    
    match theater.encrypt_with_drama(data.user_id, &data.data, level).await {
        Ok(result) => Ok(HttpResponse::Ok().json(ApiResponse {
            success: true,
            data: Some(result),
            error: None,
        })),
        Err(e) => Ok(HttpResponse::InternalServerError().json(ApiResponse::<()> {
            success: false,
            data: None,
            error: Some(e.to_string()),
        })),
    }
}

async fn funeral_handler(
    data: web::Json<FuneralRequest>,
    state: web::Data<AppState>,
) -> Result<HttpResponse> {
    let funeral_type = match data.funeral_type.as_str() {
        "viking" => FuneralType::Viking {
            longboat_size: 50,
            burning_arrows: 100,
        },
        "space" => FuneralType::Space {
            trajectory: "Mars".to_string(),
            escape_velocity: 11.2,
        },
        "quantum" => FuneralType::Quantum {
            superposition: true,
            observer_count: 42,
        },
        "eldritch" => FuneralType::Eldritch {
            tentacles: 888,
            dimensions_breached: 13,
            sanity_cost: -9999,
        },
        _ => FuneralType::Viking {
            longboat_size: 30,
            burning_arrows: 50,
        },
    };

    let mut theater = state.theater.lock().await;
    
    match theater.schedule_funeral(
        data.user_id,
        data.data_ids.clone(),
        funeral_type,