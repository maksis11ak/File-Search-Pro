// FileSearchPro.java - Поиск файлов на Java (Swing GUI)
import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;

public class FileSearchPro extends JFrame {
    private JTextField pathField, nameField, extField, minSizeField, maxSizeField, contentField;
    private JButton browseBtn, searchBtn, stopBtn, exportBtn;
    private JTable resultTable;
    private DefaultTableModel tableModel;
    private JLabel statusLabel;
    private JProgressBar progressBar;
    private volatile boolean stopSearch = false;
    private ExecutorService executor;
    private Future<?> searchFuture;
    private List<Map<String, Object>> results = new ArrayList<>();
    
    public FileSearchPro() {
        setTitle("🔍 Поиск файлов Pro");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(950, 650);
        setLocationRelativeTo(null);
        initUI();
    }
    
    private void initUI() {
        setLayout(new BorderLayout(10,10));
        JPanel topPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5,5,5,5);
        gbc.fill = GridBagConstraints.HORIZONTAL;
        
        // Папка
        gbc.gridx=0; gbc.gridy=0; topPanel.add(new JLabel("Папка:"), gbc);
        gbc.gridx=1; gbc.gridwidth=2;
        pathField = new JTextField(System.getProperty("user.dir"));
        topPanel.add(pathField, gbc);
        gbc.gridx=3; gbc.gridwidth=1;
        browseBtn = new JButton("Обзор");
        topPanel.add(browseBtn, gbc);
        
        // Имя
        gbc.gridx=0; gbc.gridy=1; topPanel.add(new JLabel("Имя (маска):"), gbc);
        gbc.gridx=1; gbc.gridwidth=2;
        nameField = new JTextField("*");
        topPanel.add(nameField, gbc);
        
        // Расширения
        gbc.gridx=0; gbc.gridy=2; topPanel.add(new JLabel("Расширения:"), gbc);
        gbc.gridx=1; gbc.gridwidth=2;
        extField = new JTextField();
        topPanel.add(extField, gbc);
        
        // Размер
        gbc.gridx=0; gbc.gridy=3; topPanel.add(new JLabel("Размер (байт):"), gbc);
        gbc.gridx=1; gbc.gridwidth=1;
        minSizeField = new JTextField(8);
        topPanel.add(minSizeField, gbc);
        gbc.gridx=2;
        maxSizeField = new JTextField(8);
        topPanel.add(maxSizeField, gbc);
        
        // Содержимое
        gbc.gridx=0; gbc.gridy=4; topPanel.add(new JLabel("Содержит текст:"), gbc);
        gbc.gridx=1; gbc.gridwidth=2;
        contentField = new JTextField();
        topPanel.add(contentField, gbc);
        
        // Кнопки
        JPanel btnPanel = new JPanel(new FlowLayout());
        searchBtn = new JButton("🔍 Найти");
        stopBtn = new JButton("⏹️ Стоп");
        stopBtn.setEnabled(false);
        exportBtn = new JButton("💾 Сохранить CSV");
        btnPanel.add(searchBtn);
        btnPanel.add(stopBtn);
        btnPanel.add(exportBtn);
        topPanel.add(btnPanel, gbc);
        
        add(topPanel, BorderLayout.NORTH);
        
        // Таблица
        tableModel = new DefaultTableModel(new String[]{"Имя", "Путь", "Размер", "Изменён"}, 0);
        resultTable = new JTable(tableModel);
        resultTable.setAutoCreateRowSorter(true);
        resultTable.addMouseListener(new MouseAdapter() {
            public void mouseClicked(MouseEvent e) {
                if (e.getClickCount() == 2) {
                    int row = resultTable.getSelectedRow();
                    String path = (String) tableModel.getValueAt(row, 1);
                    try {
                        Desktop.getDesktop().open(new File(path));
                    } catch (IOException ex) { ex.printStackTrace(); }
                }
            }
        });
        JScrollPane scroll = new JScrollPane(resultTable);
        add(scroll, BorderLayout.CENTER);
        
        // Прогресс и статус
        JPanel bottom = new JPanel(new BorderLayout());
        progressBar = new JProgressBar();
        progressBar.setIndeterminate(false);
        bottom.add(progressBar, BorderLayout.CENTER);
        statusLabel = new JLabel("Готов");
        bottom.add(statusLabel, BorderLayout.SOUTH);
        add(bottom, BorderLayout.SOUTH);
        
        browseBtn.addActionListener(e -> {
            JFileChooser fc = new JFileChooser();
            fc.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
            if (fc.showOpenDialog(this) == JFileChooser.APPROVE_OPTION) {
                pathField.setText(fc.getSelectedFile().getAbsolutePath());
            }
        });
        searchBtn.addActionListener(e -> startSearch());
        stopBtn.addActionListener(e -> stopSearch());
        exportBtn.addActionListener(e -> exportCSV());
    }
    
    private void startSearch() {
        if (searchFuture != null && !searchFuture.isDone()) return;
        stopSearch = false;
        results.clear();
        tableModel.setRowCount(0);
        searchBtn.setEnabled(false);
        stopBtn.setEnabled(true);
        exportBtn.setEnabled(false);
        progressBar.setIndeterminate(true);
        statusLabel.setText("Поиск...");
        executor = Executors.newSingleThreadExecutor();
        searchFuture = executor.submit(() -> {
            try {
                searchFiles();
            } catch (Exception ex) {
                ex.printStackTrace();
                SwingUtilities.invokeLater(() -> statusLabel.setText("Ошибка: " + ex.getMessage()));
            } finally {
                SwingUtilities.invokeLater(() -> {
                    searchBtn.setEnabled(true);
                    stopBtn.setEnabled(false);
                    progressBar.setIndeterminate(false);
                    statusLabel.setText("Готово. Найдено: " + results.size());
                    exportBtn.setEnabled(!results.isEmpty());
                });
                executor.shutdown();
            }
        });
    }
    
    private void searchFiles() throws IOException {
        Path root = Paths.get(pathField.getText());
        String namePattern = nameField.getText().trim();
        String extStr = extField.getText().trim();
        Set<String> extensions = extStr.isEmpty() ? null : new HashSet<>(Arrays.asList(extStr.toLowerCase().split(",")));
        Long minSize = parseLong(minSizeField.getText());
        Long maxSize = parseLong(maxSizeField.getText());
        String searchContent = contentField.getText().trim();
        
        String regex = namePattern.replace(".", "\\.").replace("*", ".*").replace("?", ".");
        java.util.regex.Pattern nameRegex = java.util.regex.Pattern.compile(regex, java.util.regex.Pattern.CASE_INSENSITIVE);
        
        Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                if (stopSearch) return FileVisitResult.TERMINATE;
                String fileName = file.getFileName().toString();
                if (!nameRegex.matcher(fileName).matches()) return FileVisitResult.CONTINUE;
                if (extensions != null) {
                    String ext = "";
                    int dot = fileName.lastIndexOf('.');
                    if (dot > 0) ext = fileName.substring(dot+1).toLowerCase();
                    if (!extensions.contains(ext)) return FileVisitResult.CONTINUE;
                }
                long size = attrs.size();
                if (minSize != null && size < minSize) return FileVisitResult.CONTINUE;
                if (maxSize != null && size > maxSize) return FileVisitResult.CONTINUE;
                if (!searchContent.isEmpty()) {
                    try {
                        String content = new String(Files.readAllBytes(file));
                        if (!content.toLowerCase().contains(searchContent.toLowerCase())) {
                            return FileVisitResult.CONTINUE;
                        }
                    } catch (IOException e) {
                        return FileVisitResult.CONTINUE;
                    }
                }
                Map<String, Object> map = new HashMap<>();
                map.put("name", fileName);
                map.put("path", file.toString());
                map.put("size", size);
                map.put("modified", attrs.lastModifiedTime().toString());
                results.add(map);
                SwingUtilities.invokeLater(() -> {
                    tableModel.addRow(new Object[]{fileName, file.toString(), size, attrs.lastModifiedTime().toString()});
                });
                return FileVisitResult.CONTINUE;
            }
            
            @Override
            public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                String dirName = dir.getFileName().toString();
                if (dirName.startsWith(".") || dirName.equals("node_modules") || dirName.equals("__pycache__") || dirName.equals("venv")) {
                    return FileVisitResult.SKIP_SUBTREE;
                }
                return FileVisitResult.CONTINUE;
            }
        });
    }
    
    private void stopSearch() {
        stopSearch = true;
        if (searchFuture != null) searchFuture.cancel(true);
        statusLabel.setText("Остановлено");
    }
    
    private void exportCSV() {
        JFileChooser fc = new JFileChooser();
        if (fc.showSaveDialog(this) == JFileChooser.APPROVE_OPTION) {
            try (PrintWriter pw = new PrintWriter(fc.getSelectedFile())) {
                pw.println("Имя,Путь,Размер,Изменён");
                for (Map<String, Object> r : results) {
                    pw.printf("\"%s\",\"%s\",%d,\"%s\"\n", r.get("name"), r.get("path"), r.get("size"), r.get("modified"));
                }
                JOptionPane.showMessageDialog(this, "Экспортировано " + results.size() + " записей");
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }
    }
    
    private Long parseLong(String s) {
        if (s == null || s.trim().isEmpty()) return null;
        try { return Long.parseLong(s.trim()); } catch (NumberFormatException e) { return null; }
    }
    
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new FileSearchPro().setVisible(true));
    }
}
