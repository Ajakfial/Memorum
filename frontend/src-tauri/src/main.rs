// Memorum desktop shell.
//
// Deliberately thin: there is no Rust-side business logic. The React
// frontend talks straight to the Memorum backend over HTTPS/WSS, so this
// binary's only job is to host the webview, which is what keeps the app
// fast to start and light on memory compared to bundling a full runtime
// (e.g. Electron + Node) per platform.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running Memorum");
}
