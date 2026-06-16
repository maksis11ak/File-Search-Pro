// search.go - Поиск файлов на Go (CLI с цветным выводом и параллелизмом)
package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

type FileInfo struct {
	Path string
	Size int64
	Mod  time.Time
}

var (
	pattern    string
	extensions string
	searchText string
	minSize    int64
	maxSize    int64
	workers    int
	exclude    string
)

func main() {
	root := flag.String("path", ".", "Корневая папка")
	flag.StringVar(&pattern, "name", "*", "Маска имени")
	flag.StringVar(&extensions, "ext", "", "Расширения через запятую")
	flag.StringVar(&searchText, "content", "", "Текст внутри файлов")
	flag.Int64Var(&minSize, "min-size", 0, "Минимальный размер (байт)")
	flag.Int64Var(&maxSize, "max-size", 0, "Максимальный размер (байт)")
	flag.IntVar(&workers, "workers", 4, "Количество воркеров")
	flag.StringVar(&exclude, "exclude", ".git,node_modules,__pycache__,venv", "Исключаемые папки")
	flag.Parse()

	if *root == "" {
		fmt.Println("Укажите путь")
		return
	}

	excludeSet := make(map[string]bool)
	for _, d := range strings.Split(exclude, ",") {
		excludeSet[strings.TrimSpace(d)] = true
	}

	// Регулярка для имени
	regexPattern := strings.ReplaceAll(regexp.QuoteMeta(pattern), `\*`, `.*`)
	regexPattern = strings.ReplaceAll(regexPattern, `\?`, `.`)
	nameRegex, _ := regexp.Compile("(?i)" + regexPattern)

	extList := []string{}
	if extensions != "" {
		for _, e := range strings.Split(extensions, ",") {
			extList = append(extList, strings.TrimSpace(strings.ToLower(e)))
		}
	}

	fileChan := make(chan string, 1000)
	resultChan := make(chan FileInfo, 1000)
	var wg sync.WaitGroup

	// Воркеры
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for filePath := range fileChan {
				info, err := os.Stat(filePath)
				if err != nil || info.IsDir() {
					continue
				}
				name := filepath.Base(filePath)
				if !nameRegex.MatchString(name) {
					continue
				}
				if len(extList) > 0 {
					ext := strings.ToLower(filepath.Ext(name))
					if strings.HasPrefix(ext, ".") {
						ext = ext[1:]
					}
					found := false
					for _, e := range extList {
						if e == ext {
							found = true
							break
						}
					}
					if !found {
						continue
					}
				}
				size := info.Size()
				if minSize > 0 && size < minSize {
					continue
				}
				if maxSize > 0 && size > maxSize {
					continue
				}
				if searchText != "" {
					content, err := ioutil.ReadFile(filePath)
					if err != nil {
						continue
					}
					if !strings.Contains(strings.ToLower(string(content)), strings.ToLower(searchText)) {
						continue
					}
				}
				resultChan <- FileInfo{Path: filePath, Size: size, Mod: info.ModTime()}
			}
		}()
	}

	// Обход
	go func() {
		err := filepath.WalkDir(*root, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if d.IsDir() {
				if excludeSet[d.Name()] || strings.HasPrefix(d.Name(), ".") {
					return filepath.SkipDir
				}
				return nil
			}
			fileChan <- path
			return nil
		})
		if err != nil {
			fmt.Println("Ошибка обхода:", err)
		}
		close(fileChan)
		wg.Wait()
		close(resultChan)
	}()

	results := []FileInfo{}
	for r := range resultChan {
		results = append(results, r)
		fmt.Printf("\033[32m%s\033[0m (%d байт, %s)\n", r.Path, r.Size, r.Mod.Format("2006-01-02 15:04:05"))
	}
	fmt.Printf("\n✅ Найдено файлов: %d\n", len(results))
}
