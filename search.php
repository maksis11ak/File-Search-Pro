<?php
// search.php - Поиск файлов на PHP (CLI + веб)
// CLI: php search.php /путь "*.txt" --content="текст"
// Веб: открыть в браузере

if (php_sapi_name() === 'cli') {
    // CLI режим
    if ($argc < 2) {
        echo "Использование: php search.php <папка> [маска] [--content=текст] [--ext=txt,php] [--min-size=100] [--max-size=1000]\n";
        exit(1);
    }
    $path = $argv[1];
    $pattern = $argv[2] ?? '*';
    $searchContent = null;
    $extensions = [];
    $minSize = null;
    $maxSize = null;
    for ($i = 3; $i < $argc; $i++) {
        if (strpos($argv[$i], '--content=') === 0) $searchContent = substr($argv[$i], 10);
        if (strpos($argv[$i], '--ext=') === 0) $extensions = explode(',', substr($argv[$i], 6));
        if (strpos($argv[$i], '--min-size=') === 0) $minSize = (int)substr($argv[$i], 11);
        if (strpos($argv[$i], '--max-size=') === 0) $maxSize = (int)substr($argv[$i], 11);
    }
    searchFilesCLI($path, $pattern, $extensions, $searchContent, $minSize, $maxSize);
} else {
    // Веб-режим
    ?>
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>🔍 Поиск файлов на PHP</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f4f7fb; }
            .container { max-width: 1100px; margin: 0 auto; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 10px; }
            label { display: inline-block; width: 150px; font-weight: bold; }
            input { padding: 6px; border-radius: 6px; border: 1px solid #ccc; }
            button { padding: 8px 20px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background: #2c3e50; color: white; }
            tr:hover { background: #f1f1f1; cursor: pointer; }
        </style>
    </head>
    <body>
    <div class="container">
        <h2>🔍 Поиск файлов (PHP)</h2>
        <form method="POST">
            <div class="form-group"><label>Папка:</label><input type="text" name="path" value="<?= htmlspecialchars($_POST['path'] ?? getcwd()) ?>" size="60"></div>
            <div class="form-group"><label>Маска имени:</label><input type="text" name="pattern" value="<?= htmlspecialchars($_POST['pattern'] ?? '*') ?>"></div>
            <div class="form-group"><label>Расширения (через запятую):</label><input type="text" name="extensions" value="<?= htmlspecialchars($_POST['extensions'] ?? '') ?>"></div>
            <div class="form-group"><label>Мин. размер (байт):</label><input type="number" name="min_size" value="<?= htmlspecialchars($_POST['min_size'] ?? '') ?>"></div>
            <div class="form-group"><label>Макс. размер (байт):</label><input type="number" name="max_size" value="<?= htmlspecialchars($_POST['max_size'] ?? '') ?>"></div>
            <div class="form-group"><label>Содержит текст:</label><input type="text" name="content" value="<?= htmlspecialchars($_POST['content'] ?? '') ?>"></div>
            <button type="submit">🔍 Найти</button>
        </form>
        <?php
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $path = $_POST['path'] ?? '.';
            $pattern = $_POST['pattern'] ?? '*';
            $extensions = array_filter(array_map('trim', explode(',', $_POST['extensions'] ?? '')));
            $minSize = $_POST['min_size'] ? (int)$_POST['min_size'] : null;
            $maxSize = $_POST['max_size'] ? (int)$_POST['max_size'] : null;
            $searchContent = $_POST['content'] ?? '';
            searchFilesWeb($path, $pattern, $extensions, $searchContent, $minSize, $maxSize);
        }
        ?>
    </div>
    <script>
        document.querySelectorAll('table tbody tr').forEach(row => {
            row.addEventListener('click', () => {
                const path = row.cells[1]?.innerText;
                if (path) alert('Открыть файл? ' + path);
            });
        });
    </script>
    </body>
    </html>
    <?php
}

function searchFilesCLI($path, $pattern, $extensions, $searchContent, $minSize, $maxSize) {
    $regex = '/^' . str_replace(['*', '?'], ['.*', '.'], preg_quote($pattern, '/')) . '$/i';
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($path, RecursiveDirectoryIterator::SKIP_DOTS));
    $count = 0;
    foreach ($iterator as $file) {
        if ($file->isDir()) continue;
        $name = $file->getFilename();
        if (!preg_match($regex, $name)) continue;
        $ext = strtolower($file->getExtension());
        if (!empty($extensions) && !in_array($ext, $extensions)) continue;
        $size = $file->getSize();
        if ($minSize !== null && $size < $minSize) continue;
        if ($maxSize !== null && $size > $maxSize) continue;
        if (!empty($searchContent)) {
            $content = @file_get_contents($file->getRealPath());
            if ($content === false || stripos($content, $searchContent) === false) continue;
        }
        echo $file->getRealPath() . " (" . $size . " bytes, " . date('Y-m-d H:i:s', $file->getMTime()) . ")\n";
        $count++;
    }
    echo "\n✅ Найдено файлов: $count\n";
}

function searchFilesWeb($path, $pattern, $extensions, $searchContent, $minSize, $maxSize) {
    $regex = '/^' . str_replace(['*', '?'], ['.*', '.'], preg_quote($pattern, '/')) . '$/i';
    $results = [];
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($path, RecursiveDirectoryIterator::SKIP_DOTS));
    foreach ($iterator as $file) {
        if ($file->isDir()) continue;
        $name = $file->getFilename();
        if (!preg_match($regex, $name)) continue;
        $ext = strtolower($file->getExtension());
        if (!empty($extensions) && !in_array($ext, $extensions)) continue;
        $size = $file->getSize();
        if ($minSize !== null && $size < $minSize) continue;
        if ($maxSize !== null && $size > $maxSize) continue;
        if (!empty($searchContent)) {
            $content = @file_get_contents($file->getRealPath());
            if ($content === false || stripos($content, $searchContent) === false) continue;
        }
        $results[] = [
            'name' => $name,
            'path' => $file->getRealPath(),
            'size' => $size,
            'modified' => date('Y-m-d H:i:s', $file->getMTime())
        ];
    }
    if (empty($results)) {
        echo "<p>Ничего не найдено.</p>";
    } else {
        echo "<table><thead><tr><th>Имя</th><th>Путь</th><th>Размер</th><th>Изменён</th></tr></thead><tbody>";
        foreach ($results as $r) {
            echo "<tr><td>{$r['name']}</td><td>{$r['path']}</td><td>{$r['size']}</td><td>{$r['modified']}</td></tr>";
        }
        echo "</tbody></table><p>Найдено: " . count($results) . "</p>";
    }
}
?>
