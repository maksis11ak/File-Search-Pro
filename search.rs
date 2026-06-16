// search.rs - Поиск файлов на Rust (асинхронный, параллельный)
// Зависимости: walkdir, ignore, rayon, colored, clap, regex
use clap::Parser;
use walkdir::WalkDir;
use regex::Regex;
use colored::*;
use std::fs;
use std::path::Path;
use rayon::prelude::*;

#[derive(Parser)]
#[command(name = "search", about = "Поиск файлов")]
struct Args {
    #[arg(help = "Корневая папка")]
    path: String,
    #[arg(short, long, default_value = "*")]
    name: String,
    #[arg(short, long, help = "Расширения через запятую")]
    ext: Option<String>,
    #[arg(short, long, help = "Текст для поиска внутри")]
    content: Option<String>,
    #[arg(long, help = "Мин. размер (байт)")]
    min_size: Option<u64>,
    #[arg(long, help = "Макс. размер (байт)")]
    max_size: Option<u64>,
    #[arg(short, long, default_value = "4")]
    threads: usize,
    #[arg(long, default_value = ".git,node_modules,__pycache__,venv")]
    exclude: String,
}

fn main() {
    let args = Args::parse();
    let exclude_set: std::collections::HashSet<String> = args.exclude.split(',').map(|s| s.trim().to_string()).collect();
    
    let name_regex = {
        let pattern = regex::escape(&args.name).replace("\\*", ".*").replace("\\?", ".");
        Regex::new(&format!("(?i)^{}$", pattern)).unwrap()
    };
    
    let ext_list: Vec<String> = args.ext.unwrap_or_default()
        .split(',')
        .map(|s| s.trim().to_lowercase())
        .filter(|s| !s.is_empty())
        .collect();
    
    let walker = WalkDir::new(&args.path)
        .into_iter()
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            !exclude_set.contains(&name.to_string()) && !name.starts_with('.')
        })
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());
    
    let files: Vec<_> = walker.collect();
    
    let results: Vec<_> = files.par_iter()
        .with_min_len(10)
        .filter(|entry| {
            let name = entry.file_name().to_string_lossy();
            if !name_regex.is_match(&name) {
                return false;
            }
            if !ext_list.is_empty() {
                let ext = Path::new(&*name).extension()
                    .and_then(|e| e.to_str())
                    .map(|e| e.to_lowercase())
                    .unwrap_or_default();
                if !ext_list.contains(&ext) {
                    return false;
                }
            }
            if let Ok(metadata) = entry.metadata() {
                let size = metadata.len();
                if let Some(min) = args.min_size { if size < min { return false; } }
                if let Some(max) = args.max_size { if size > max { return false; } }
                if let Some(ref text) = args.content {
                    if let Ok(content) = fs::read_to_string(entry.path()) {
                        if !content.to_lowercase().contains(&text.to_lowercase()) {
                            return false;
                        }
                    } else {
                        return false;
                    }
                }
                true
            } else {
                false
            }
        })
        .map(|entry| {
            let meta = entry.metadata().unwrap();
            (entry.path().to_path_buf(), meta.len(), meta.modified().unwrap())
        })
        .collect();
    
    for (path, size, modified) in &results {
        println!("{} ({} bytes, {:?})", path.display().to_string().green(), size, modified);
    }
    println!("\n✅ Найдено файлов: {}", results.len());
}
