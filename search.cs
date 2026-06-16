// search.cs - Поиск файлов на C# (Windows Forms)
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace FileSearchPro
{
    public partial class MainForm : Form
    {
        private TextBox folderBox, nameBox, extBox, minSizeBox, maxSizeBox, contentBox;
        private Button browseBtn, searchBtn, stopBtn, exportBtn;
        private DataGridView resultsGrid;
        private Label statusLabel;
        private ProgressBar progressBar;
        private CancellationTokenSource cts;
        private List<SearchResult> results = new List<SearchResult>();
        
        public MainForm()
        {
            InitializeComponent();
            SetupUI();
        }
        
        private void SetupUI()
        {
            this.Text = "🔍 Поиск файлов Pro (C#)";
            this.Size = new System.Drawing.Size(1000, 650);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            var mainPanel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 2 };
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 200));
            mainPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            
            var filterPanel = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, Padding = new Padding(10), AutoSize = true };
            filterPanel.Controls.Add(CreateFilterRow("Папка:", ref folderBox, ref browseBtn, true));
            filterPanel.Controls.Add(CreateSimpleRow("Имя (маска):", ref nameBox, "*"));
            filterPanel.Controls.Add(CreateSimpleRow("Расширения (через запятую):", ref extBox, ""));
            filterPanel.Controls.Add(CreateSizeRow());
            filterPanel.Controls.Add(CreateSimpleRow("Содержит текст:", ref contentBox, ""));
            
            var btnPanel = new FlowLayoutPanel();
            searchBtn = new Button { Text = "🔍 Найти", Width = 100 };
            stopBtn = new Button { Text = "⏹️ Стоп", Width = 100, Enabled = false };
            exportBtn = new Button { Text = "💾 Сохранить CSV", Width = 120 };
            btnPanel.Controls.Add(searchBtn);
            btnPanel.Controls.Add(stopBtn);
            btnPanel.Controls.Add(exportBtn);
            filterPanel.Controls.Add(btnPanel);
            
            mainPanel.Controls.Add(filterPanel, 0, 0);
            
            resultsGrid = new DataGridView { Dock = DockStyle.Fill, AllowUserToAddRows = false, ReadOnly = true, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill };
            resultsGrid.Columns.Add("Name", "Имя");
            resultsGrid.Columns.Add("Path", "Путь");
            resultsGrid.Columns.Add("Size", "Размер (байт)");
            resultsGrid.Columns.Add("Modified", "Изменён");
            resultsGrid.CellDoubleClick += (s, e) => {
                if (e.RowIndex >= 0) {
                    string path = resultsGrid.Rows[e.RowIndex].Cells["Path"].Value.ToString();
                    System.Diagnostics.Process.Start(path);
                }
            };
            mainPanel.Controls.Add(resultsGrid, 0, 1);
            
            var statusPanel = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 30 };
            progressBar = new ProgressBar { Width = 200, Height = 20, Style = ProgressBarStyle.Marquee, Visible = false };
            statusLabel = new Label { Text = "Готов", AutoSize = true };
            statusPanel.Controls.Add(statusLabel);
            statusPanel.Controls.Add(progressBar);
            mainPanel.Controls.Add(statusPanel, 0, 2);
            
            this.Controls.Add(mainPanel);
            
            browseBtn.Click += (s, e) => {
                using (var fbd = new FolderBrowserDialog()) {
                    if (fbd.ShowDialog() == DialogResult.OK) folderBox.Text = fbd.SelectedPath;
                }
            };
            searchBtn.Click += async (s, e) => await StartSearch();
            stopBtn.Click += (s, e) => { cts?.Cancel(); };
            exportBtn.Click += (s, e) => ExportCSV();
        }
        
        private Panel CreateFilterRow(string label, ref TextBox textBox, ref Button button, bool withButton)
        {
            var panel = new Panel { Height = 35 };
            var lbl = new Label { Text = label, Left = 5, Top = 8, Width = 100 };
            textBox = new TextBox { Left = 110, Top = 5, Width = 300 };
            panel.Controls.Add(lbl);
            panel.Controls.Add(textBox);
            if (withButton) {
                button = new Button { Text = "Обзор", Left = 420, Top = 4, Width = 70 };
                panel.Controls.Add(button);
            }
            return panel;
        }
        
        private Panel CreateSimpleRow(string label, ref TextBox textBox, string defaultValue)
        {
            var panel = new Panel { Height = 35 };
            var lbl = new Label { Text = label, Left = 5, Top = 8, Width = 100 };
            textBox = new TextBox { Left = 110, Top = 5, Width = 300, Text = defaultValue };
            panel.Controls.Add(lbl);
            panel.Controls.Add(textBox);
            return panel;
        }
        
        private Panel CreateSizeRow()
        {
            var panel = new Panel { Height = 35 };
            var lbl = new Label { Text = "Размер (байт):", Left = 5, Top = 8, Width = 100 };
            minSizeBox = new TextBox { Left = 110, Top = 5, Width = 80, PlaceholderText = "min" };
            maxSizeBox = new TextBox { Left = 200, Top = 5, Width = 80, PlaceholderText = "max" };
            panel.Controls.Add(lbl);
            panel.Controls.Add(minSizeBox);
            panel.Controls.Add(maxSizeBox);
            return panel;
        }
        
        private async Task StartSearch()
        {
            if (!Directory.Exists(folderBox.Text)) {
                MessageBox.Show("Папка не существует");
                return;
            }
            results.Clear();
            resultsGrid.Rows.Clear();
            searchBtn.Enabled = false;
            stopBtn.Enabled = true;
            exportBtn.Enabled = false;
            progressBar.Visible = true;
            statusLabel.Text = "Поиск...";
            cts = new CancellationTokenSource();
            try {
                await Task.Run(() => SearchFiles(cts.Token), cts.Token);
                statusLabel.Text = $"Готово. Найдено: {results.Count}";
                exportBtn.Enabled = results.Count > 0;
            } catch (OperationCanceledException) {
                statusLabel.Text = "Поиск остановлен";
            } finally {
                searchBtn.Enabled = true;
                stopBtn.Enabled = false;
                progressBar.Visible = false;
            }
        }
        
        private void SearchFiles(CancellationToken token)
        {
            string root = folderBox.Text;
            string nameMask = nameBox.Text.Trim();
            string extStr = extBox.Text.Trim();
            var extensions = string.IsNullOrEmpty(extStr) ? null : extStr.Split(',').Select(e => e.Trim().ToLower()).ToHashSet();
            long? minSize = ParseLong(minSizeBox.Text);
            long? maxSize = ParseLong(maxSizeBox.Text);
            string searchContent = contentBox.Text.Trim().ToLower();
            
            var regex = WildcardToRegex(nameMask);
            var files = Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories);
            foreach (var file in files) {
                if (token.IsCancellationRequested) throw new OperationCanceledException();
                string fileName = Path.GetFileName(file);
                if (!System.Text.RegularExpressions.Regex.IsMatch(fileName, regex, System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                    continue;
                string ext = Path.GetExtension(file).TrimStart('.').ToLower();
                if (extensions != null && !extensions.Contains(ext)) continue;
                var info = new FileInfo(file);
                if (minSize.HasValue && info.Length < minSize.Value) continue;
                if (maxSize.HasValue && info.Length > maxSize.Value) continue;
                if (!string.IsNullOrEmpty(searchContent)) {
                    try {
                        string content = File.ReadAllText(file);
                        if (!content.ToLower().Contains(searchContent)) continue;
                    } catch { continue; }
                }
                lock (results) {
                    results.Add(new SearchResult { Name = fileName, Path = file, Size = info.Length, Modified = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss") });
                }
                Invoke(new Action(() => {
                    resultsGrid.Rows.Add(fileName, file, info.Length, info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"));
                }));
            }
        }
        
        private string WildcardToRegex(string pattern)
        {
            return "^" + System.Text.RegularExpressions.Regex.Escape(pattern).Replace("\\*", ".*").Replace("\\?", ".") + "$";
        }
        
        private long? ParseLong(string s)
        {
            if (long.TryParse(s, out long val)) return val;
            return null;
        }
        
        private void ExportCSV()
        {
            var saveDialog = new SaveFileDialog { Filter = "CSV files|*.csv", DefaultExt = "csv" };
            if (saveDialog.ShowDialog() == DialogResult.OK) {
                using (var sw = new StreamWriter(saveDialog.FileName, false, Encoding.UTF8)) {
                    sw.WriteLine("Имя,Путь,Размер,Изменён");
                    foreach (var r in results) {
                        sw.WriteLine($"\"{r.Name}\",\"{r.Path}\",{r.Size},\"{r.Modified}\"");
                    }
                }
                MessageBox.Show($"Сохранено {results.Count} записей");
            }
        }
        
        private class SearchResult
        {
            public string Name { get; set; }
            public string Path { get; set; }
            public long Size { get; set; }
            public string Modified { get; set; }
        }
    }
    
    static class Program
    {
        [STAThread]
        static void Main() {
            Application.EnableVisualStyles();
            Application.Run(new MainForm());
        }
    }
}
