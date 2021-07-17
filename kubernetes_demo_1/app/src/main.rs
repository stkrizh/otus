use actix_web::middleware::Logger;
use actix_web::{get, web, App, HttpResponse, HttpServer, Responder};
use env_logger::Env;

#[get("/health")]
async fn hello() -> impl Responder {
    HttpResponse::Ok()
        .header("content-type", "application/json")
        .body("{\"status\": \"OK\"}")
}

#[get("/name/{name}")]
async fn name(path: web::Path<(String,)>) -> impl Responder {
    HttpResponse::Ok()
        .header("content-type", "application/json")
        .body(format!("{{\"name\": \"{}\"}}", path.into_inner().0))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::Builder::from_env(Env::default().default_filter_or("info")).init();

    HttpServer::new(|| {
        App::new()
            .wrap(Logger::default())
            .service(hello)
            .service(name)
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
