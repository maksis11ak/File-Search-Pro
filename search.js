// search.js - Поиск файлов на Node.js (CLI)
// Использование: node search.js /путь "маска" [--content "текст"] [--ext txt,js] [--min-size 100] [--max-size 1000]

const fs = require('fs');
const path = require('path');
const { glob } = require('glob');
const { program } = require('commander');

program
  .argument('<path>', 'Корневая папка')
  .option('-n, --name <pattern>', 'Маска имени (по умолчанию *)', '*')
  .option('-e, --ext <extensions>', 'Расширения через запятую')
  .option('--min-size <bytes>', 'Минимальный размер (байт)', parseInt)
  .option('--max-size <bytes>', 'Максимальный размер (байт)', parseInt)
  .option('-c, --content <text>', 'Поиск текста внутри файлов')
  .option('-x, --exclude <dirs>', 'Исключаемые папки (через запятую)', '.git,node_modules,__pycache__,venv')
  .parse(process.argv);

const opts = program.opts();
const root = program.args[0];
const pattern = opts.name;
const extList = opts.ext ? opts.ext.split(',').map(e => e.trim()) : [];
const minSize = opts.minSize;
const maxSize = opts.maxSize;
const searchText = opts.content;
const excludeDirs = new Set(opts.exclude.split(','));

function walkDir(dir, fileList = []) {
  const items = fs.readdirSync(dir, { withFileTypes: true });
  for (const item of items) {
    const fullPath = path.join(dir, item.name);
    if (item.isDirectory()) {
      if (!excludeDirs.has(item.name) && !item.name.startsWith('.')) {
        walkDir(fullPath, fileList);
      }
    } else {
      fileList.push(fullPath);
    }
  }
  return fileList;
}

function matchesPattern(filename, pattern) {
  const regex = new RegExp('^' + pattern.replace(/\./g, '\\.').replace(/\*/g, '.*').replace(/\?/g, '.') + '$', 'i');
  return regex.test(filename);
}

function matchesExtensions(filename, extList) {
  if (!extList.length) return true;
  const ext = path.extname(filename).slice(1).toLowerCase();
  return extList.includes(ext);
}

function searchInFile(filepath, searchText) {
  if (!searchText) return true;
  try {
    const content = fs.readFileSync(filepath, 'utf8');
    return content.toLowerCase().includes(searchText.toLowerCase());
  } catch {
    return false;
  }
}

function main() {
  console.log('🔍 Поиск файлов...');
  const files = walkDir(root);
  const results = [];
  for (const file of files) {
    const name = path.basename(file);
    if (!matchesPattern(name, pattern)) continue;
    if (!matchesExtensions(name, extList)) continue;
    const stats = fs.statSync(file);
    if (minSize && stats.size < minSize) continue;
    if (maxSize && stats.size > maxSize) continue;
    if (!searchInFile(file, searchText)) continue;
    results.push({
      path: file,
      size: stats.size,
      modified: stats.mtime.toISOString().slice(0, 19).replace('T', ' ')
    });
  }
  for (const r of results) {
    console.log(`${r.path}  (${r.size} байт, ${r.modified})`);
  }
  console.log(`\n✅ Найдено файлов: ${results.length}`);
}

main();
