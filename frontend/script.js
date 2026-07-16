const form = document.querySelector("#processForm");
const projectNumber = document.querySelector("#projectNumber");
const wireField = document.querySelector("#wireField");
const wirePicker = document.querySelector("#wirePicker");
const wireTrigger = document.querySelector("#wireTrigger");
const wireMenu = document.querySelector("#wireMenu");
const wireValue = document.querySelector("#wireValue");
const wireOptions = [...document.querySelectorAll("#wireMenu .language-picker__option")];
const wireSelectionMode = document.querySelector("#wireSelectionMode");
const wireManualValue = document.querySelector("#wireManualValue");
const wireHint = document.querySelector("#wireHint");
const tuFile = document.querySelector("#tuFile");
const planFile = document.querySelector("#planFile");
const tuName = document.querySelector("#tuName");
const planName = document.querySelector("#planName");
const notice = document.querySelector("#notice");
const runState = document.querySelector("#runState");
const startButton = document.querySelector("#startButton");
const downloadNote = document.querySelector("#downloadNote");
const downloadPdf = document.querySelector("#downloadPdf");
const addParallelProject = document.querySelector("#addParallelProject");
const projectsList = document.querySelector("#projectsList");
const projectsCount = document.querySelector("#projectsCount");
let lastNoteDownloadUrl = "/api/download/note";
let selectedRunId = "";
let activeJobsCount = 0;
let projectsListBound = false;
const projectRuns = [];
const statusItems = [...document.querySelectorAll(".status-item")];
const cursorLight = document.querySelector("#cursorLight");
const liquidTargets = [...document.querySelectorAll(".liquid-control")];
const themeToggle = document.querySelector("#themeToggle");
const languagePicker = document.querySelector("#languagePicker");
const languageTrigger = document.querySelector("#languageTrigger");
const languageMenu = document.querySelector("#languageMenu");
const languageFlag = document.querySelector("#languageFlag");
const languageName = document.querySelector("#languageName");
const languageOptions = [...document.querySelectorAll("#languageMenu .language-picker__option")];
const openCheckPanel = document.querySelector("#openCheckPanel");
const closeCheckPanel = document.querySelector("#closeCheckPanel");
const checkPanel = document.querySelector("#checkPanel");
const checkPanelBackdrop = document.querySelector("#checkPanelBackdrop");
const checkForm = document.querySelector("#checkForm");
const useMainFormFiles = document.querySelector("#useMainFormFiles");
const checkTuFile = document.querySelector("#checkTuFile");
const checkPlanFile = document.querySelector("#checkPlanFile");
const checkNoteFile = document.querySelector("#checkNoteFile");
const checkTuName = document.querySelector("#checkTuName");
const checkPlanName = document.querySelector("#checkPlanName");
const checkNoteName = document.querySelector("#checkNoteName");
const runCheckButton = document.querySelector("#runCheckButton");
const checkResults = document.querySelector("#checkResults");
const checkSummary = document.querySelector("#checkSummary");
const checkArmature = document.querySelector("#checkArmature");
const checkArmatureList = document.querySelector("#checkArmatureList");
const checkIssueList = document.querySelector("#checkIssueList");
const yopkBackdrop = document.querySelector("#yopkBackdrop");
const yopkPanel = document.querySelector("#yopkPanel");
const yopkIntermediate = document.querySelector("#yopkIntermediate");
const yopkAnchor = document.querySelector("#yopkAnchor");
const branchPoleType = document.querySelector("#branchPoleType");

const LANGUAGE_META = {
  ru: { flag: "🇷🇺", name: "Русский" },
  en: { flag: "🇬🇧", name: "English" },
  de: { flag: "🇩🇪", name: "Deutsch" },
  it: { flag: "🇮🇹", name: "Italiano" },
};

const projectNumberPattern = /^ПСД\/48\/2026\/\d{3}(?:-[А-ЯA-Z0-9]+)?$/;

let currentWireValue = "auto";

const WIRE_OPTION_LABELS = {
  auto: { titleKey: "wireAuto", metaKey: "wireAutoMeta" },
  "manual:3*70+1*70": { title: "3х70+1х70", metaKey: "wireManualMeta" },
  "manual:3*50+1*54,6": { title: "3х50+1х54,6", metaKey: "wireManualMeta" },
  "manual:3*35+1*35": { title: "3х35+1х35", metaKey: "wireManualMeta" },
};

const translations = {
  ru: {
    brand: "Автоматизация ТУ",
    systemStatus: "Инженерная система подготовки документации",
    languageLabel: "Язык",
    themeLight: "Светлая тема",
    themeDark: "Темная тема",
    eyebrow: "Локальный инженерный контур",
    heroTitle: "Автоматизация подготовки документации по ТУ",
    heroCopy: "Загрузите ТУ и готовый DWG/DXF-план, укажите номер проекта — система подготовит пояснительную записку.",
    inputData: "Исходные данные",
    idle: "Ожидание",
    projectNumber: "Номер проекта",
    wirePanelEyebrow: "Ключевой параметр",
    wirePanelTitle: "Выбор провода",
    wirePanelSubtitle: "Выберите сечение вручную или оставьте автоматическое определение из ТУ",
    wireModeAuto: "Авто",
    wireModeManual: "Вручную",
    wireAuto: "Автоматически",
    wireAutoMeta: "Из технических условий",
    wireManualMeta: "Ручной выбор",
    uploadSection: "Загрузка исходных файлов",
    wireHintAuto: "Система определит провод сама",
    wireHintManual: "Выбран вручную: {wire}. Автоматическое определение будет переопределено.",
    wireResultAuto: "Автоматически определено: {auto}. Итоговый провод: {final}.",
    wireResultManual: "Автоматически определено: {auto}. Итоговый провод: {final}.",
    tuUpload: "ТУ DOCX/PDF",
    planUpload: "План DWG/DXF",
    noFile: "Файл не выбран",
    processingStatus: "Статус обработки",
    stepFiles: "Файлы загружены",
    stepTu: "Данные из ТУ извлечены",
    stepPlan: "План проанализирован",
    stepMap: "Карта замен создана",
    stepDwg: "Записка заполнена",
    stepDone: "Готово",
    cardOneTitle: "Заполнить записку",
    cardOneText: "Введите номер, добавьте ТУ и план — система подготовит DWG-записку с нужными данными.",
    cardTwoTitle: "Проверить план",
    cardTwoText: "Приложение посчитает длину линии, опоры и заземления без изменения исходного чертежа.",
    cardThreeTitle: "Собрать комплект",
    cardThreeText: "После обработки можно скачать готовую записку по каждому проекту отдельно.",
    footer: "Автоматизация ТУ — инженерный инструмент для подготовки проектной документации",
    dockStart: "Старт",
    dockNote: "Скачать записку",
    dockPdf: "Скачать PDF",
    addParallelProject: "Параллельный проект",
    projectsListTitle: "Готовые проекты",
    projectsListHint: "Можно запустить второй проект параллельно и скачать каждый отдельно.",
    parallelFormReady: "Форма очищена. Загрузите ТУ и план для следующего проекта — предыдущие скачивания сохранятся.",
    projectRunning: "Обрабатывается…",
    projectReady: "Готов к скачиванию",
    projectFailed: "Ошибка",
    projectDownloadNote: "Записка",
    projectDownloadPdf: "PDF",
    projectType04: "0,4 кВ",
    projectType10: "10 кВ",
    stateFiles: "Передача файлов",
    stateTu: "Чтение ТУ",
    statePlan: "Анализ плана",
    stateMap: "Создание карты замен",
    stateDwg: "Заполнение DWG",
    statePdf: "Готово",
    ready: "Готово",
    check: "Проверьте",
    error: "Ошибка",
    validationProjectEmpty: "Введите номер проекта.",
    validationProjectFormat: "Номер проекта должен соответствовать формату ПСД/48/2026/XXX или ПСД/48/2026/XXX-СУФФИКС.",
    validationTu: "Выберите файл ТУ DOCX/PDF.",
    validationPlan: "Выберите файл плана DWG/DXF.",
    processError: "Не удалось обработать проект.",
    networkError: "Сервер не ответил. Обновите страницу и запустите проект ещё раз.",
    processingStarted: "Обработка запущена: чтение ТУ, расчёт и заполнение записки. PDF не создаётся.",
    unresolved: "Часть полей не заменена:",
    checkLog: "Проверьте log.txt.",
    success: "Пояснительная записка сформирована. Поля заменены.",
    success10kv: "10 кВ: сформирован заполненный DXF — placeholders заменены, структура эталона сохранена.",
    pdfUnavailable: "PDF отключён.",
    checkPanelOpen: "Проверка",
    checkPanelClose: "Закрыть",
    checkPanelEyebrow: "Предварительная проверка",
    checkPanelTitle: "Проверка исходных файлов",
    checkPanelCopy: "Загрузите ТУ, план и пояснительную записку. Система проверит извлекаемые данные, опоры на плане и placeholders в записке.",
    checkPanelReuse: "Использовать файлы из основной формы, если они уже выбраны",
    checkNoteUpload: "Записка DWG/DXF",
    checkPanelNoteHint: "Если записку не загрузить, будет проверен эталонный шаблон, который система выберет автоматически.",
    checkPanelRun: "Проверить",
    checkPanelRunning: "Проверка...",
    validationCheckTu: "Выберите файл ТУ для проверки.",
    validationCheckPlan: "Выберите файл плана для проверки.",
    checkSummaryReady: "Критичных ошибок не найдено.",
    checkSummaryWarningsOnly: "Критичных ошибок нет. Предупреждений: {warnings}.",
    checkSummaryIssues: "Найдено ошибок: {errors}, предупреждений: {warnings}.",
    checkCategoryTu: "ТУ",
    checkCategoryPlan: "План",
    checkCategoryNote: "Записка",
    checkCategoryCross: "Связка",
    checkCategoryWire: "Провод",
    checkCategoryProject: "Проект",
    checkCategoryArmature: "Арматура",
    checkArmatureTitle: "Расчёт арматуры по плану",
    checkSeverityError: "Ошибка",
    checkSeverityWarning: "Внимание",
    checkSeverityInfo: "Инфо",
    yopkEyebrow: "Проект 10 кВ",
    yopkTitle: "От какой опоры ответвляемся?",
    yopkCopy: "Выберите тип узла ответвления для заполнения поля {{YOPK}} в пояснительной записке.",
    yopkIntermediate: "От промежуточной (УОП)",
    yopkAnchor: "От анкерной (УОК)",
  },
  en: {
    brand: "TU Automation",
    systemStatus: "Engineering documentation system",
    languageLabel: "Language",
    themeLight: "Light theme",
    themeDark: "Dark theme",
    eyebrow: "Local engineering workspace",
    heroTitle: "Automated TU documentation preparation",
    heroCopy: "Upload TU and a finished DWG/DXF plan, enter the project number, and the system will prepare the note and PDF package.",
    inputData: "Input data",
    idle: "Waiting",
    projectNumber: "Project number",
    wirePanelEyebrow: "Key parameter",
    wirePanelTitle: "Wire selection",
    wirePanelSubtitle: "Choose a section manually or keep automatic detection from TU",
    wireModeAuto: "Auto",
    wireModeManual: "Manual",
    wireAuto: "Automatic",
    wireAutoMeta: "From technical conditions",
    wireManualMeta: "Manual selection",
    uploadSection: "Upload source files",
    wireHintAuto: "The system will detect the wire automatically",
    wireHintManual: "Selected manually: {wire}. Automatic detection will be overridden.",
    wireResultAuto: "Auto-detected: {auto}. Final wire: {final}.",
    wireResultManual: "Auto-detected: {auto}. Final wire: {final}.",
    tuUpload: "TU DOCX/PDF",
    planUpload: "Plan DWG/DXF",
    noFile: "No file selected",
    processingStatus: "Processing status",
    stepFiles: "Files uploaded",
    stepTu: "TU data extracted",
    stepPlan: "Plan analyzed",
    stepMap: "Replacement map created",
    stepDwg: "Note filled",
    stepDone: "Done",
    cardOneTitle: "Fill the note",
    cardOneText: "Enter the number, add TU and the plan, and the system prepares the DWG note with the required data.",
    cardTwoTitle: "Check the plan",
    cardTwoText: "The app counts line length, supports, and grounding without changing the source drawing.",
    cardThreeTitle: "Build the package",
    cardThreeText: "After processing, download the note and final PDF when export is available.",
    footer: "TU Automation — an engineering tool for project documentation",
    dockStart: "Start",
    dockNote: "Download note",
    dockPdf: "Download PDF",
    addParallelProject: "Parallel project",
    projectsListTitle: "Ready projects",
    projectsListHint: "You can start a second project in parallel and download each one separately.",
    parallelFormReady: "Form cleared. Upload TU and plan for the next project — previous downloads stay available.",
    projectRunning: "Processing…",
    projectReady: "Ready to download",
    projectFailed: "Error",
    projectDownloadNote: "Note",
    projectDownloadPdf: "PDF",
    projectType04: "0.4 kV",
    projectType10: "10 kV",
    stateFiles: "Uploading files",
    stateTu: "Reading TU",
    statePlan: "Analyzing plan",
    stateMap: "Creating replacement map",
    stateDwg: "Filling DWG",
    statePdf: "Building PDF",
    ready: "Done",
    check: "Check",
    error: "Error",
    validationProjectEmpty: "Enter the project number.",
    validationProjectFormat: "Project number must match ПСД/48/2026/XXX or ПСД/48/2026/XXX-SUFFIX.",
    validationTu: "Choose a TU DOCX/PDF file.",
    validationPlan: "Choose a DWG/DXF plan file.",
    processError: "Could not process the project.",
    processingStarted: "Processing started. This usually takes 3–8 minutes: TU parsing, distance calculation, DWG fill, and PDF export.",
    unresolved: "Some placeholders were not replaced:",
    checkLog: "Check log.txt.",
    success: "The note has been generated. Placeholders were replaced.",
    success10kv: "10 kV note generated. Placeholders replaced in note_result.dwg.",
    pdfUnavailable: "PDF is not available yet.",
    checkPanelOpen: "Validate",
    checkPanelClose: "Close",
    checkPanelEyebrow: "Pre-flight check",
    checkPanelTitle: "Validate source files",
    checkPanelCopy: "Upload TU, plan, and note. The system checks extracted data, plan supports, and note placeholders.",
    checkPanelReuse: "Use files from the main form when already selected",
    checkNoteUpload: "Note DWG/DXF",
    checkPanelNoteHint: "If no note is uploaded, the auto-selected template will be checked instead.",
    checkPanelRun: "Validate",
    checkPanelRunning: "Validating...",
    validationCheckTu: "Choose a TU file for validation.",
    validationCheckPlan: "Choose a plan file for validation.",
    checkSummaryReady: "No critical errors found.",
    checkSummaryWarningsOnly: "No critical errors. Warnings: {warnings}.",
    checkSummaryIssues: "Errors: {errors}, warnings: {warnings}.",
    checkCategoryTu: "TU",
    checkCategoryPlan: "Plan",
    checkCategoryNote: "Note",
    checkCategoryCross: "Cross-check",
    checkCategoryWire: "Wire",
    checkCategoryProject: "Project",
    checkCategoryArmature: "Armature",
    checkArmatureTitle: "Armature calculation from plan",
    checkSeverityError: "Error",
    checkSeverityWarning: "Warning",
    checkSeverityInfo: "Info",
    yopkEyebrow: "10 kV project",
    yopkTitle: "Which pole is the branch from?",
    yopkCopy: "Choose the branch node type for the {{YOPK}} placeholder in the explanatory note.",
    yopkIntermediate: "From intermediate (UOP)",
    yopkAnchor: "From anchor (UOK)",
  },
  de: {
    brand: "TU-Automatisierung",
    systemStatus: "System fur technische Dokumentation",
    languageLabel: "Sprache",
    themeLight: "Helles Design",
    themeDark: "Dunkles Design",
    eyebrow: "Lokaler Engineering-Arbeitsbereich",
    heroTitle: "Automatisierte Dokumentation nach TU",
    heroCopy: "Laden Sie TU und den fertigen DWG/DXF-Plan hoch, geben Sie die Projektnummer ein, und das System erstellt Notiz und PDF-Paket.",
    inputData: "Eingaben",
    idle: "Warten",
    projectNumber: "Projektnummer",
    wirePanelEyebrow: "Schlusselparameter",
    wirePanelTitle: "Leiterauswahl",
    wirePanelSubtitle: "Querschnitt manuell wahlen oder automatische Erkennung aus TU belassen",
    wireModeAuto: "Auto",
    wireModeManual: "Manuell",
    wireAuto: "Automatisch",
    wireAutoMeta: "Aus technischen Bedingungen",
    wireManualMeta: "Manuelle Auswahl",
    uploadSection: "Quelldateien hochladen",
    wireHintAuto: "Das System erkennt den Leiter automatisch",
    wireHintManual: "Manuell gewahlt: {wire}. Automatische Erkennung wird uberschrieben.",
    wireResultAuto: "Automatisch erkannt: {auto}. Endgultiger Leiter: {final}.",
    wireResultManual: "Automatisch erkannt: {auto}. Endgultiger Leiter: {final}.",
    tuUpload: "TU DOCX/PDF",
    planUpload: "Plan DWG/DXF",
    noFile: "Keine Datei ausgewahlt",
    processingStatus: "Bearbeitungsstatus",
    stepFiles: "Dateien geladen",
    stepTu: "TU-Daten gelesen",
    stepPlan: "Plan analysiert",
    stepMap: "Ersetzungskarte erstellt",
    stepDwg: "Notiz ausgefullt",
    stepDone: "Fertig",
    cardOneTitle: "Notiz ausfullen",
    cardOneText: "Nummer eingeben, TU und Plan hinzufugen — das System erstellt die DWG-Notiz mit den passenden Daten.",
    cardTwoTitle: "Plan prufen",
    cardTwoText: "Die App zahlt Leitungslange, Stutzen und Erdungen ohne die Quelldatei zu andern.",
    cardThreeTitle: "Paket erstellen",
    cardThreeText: "Nach der Verarbeitung konnen Notiz und PDF heruntergeladen werden, sobald der Export verfugbar ist.",
    footer: "TU-Automatisierung — Werkzeug fur Projektdokumentation",
    dockStart: "Start",
    dockNote: "Notiz laden",
    dockPdf: "PDF laden",
    stateFiles: "Dateien ubertragen",
    stateTu: "TU lesen",
    statePlan: "Plan analysieren",
    stateMap: "Ersetzungskarte erstellen",
    stateDwg: "DWG ausfullen",
    statePdf: "PDF erstellen",
    ready: "Fertig",
    check: "Prufen",
    error: "Fehler",
    validationProjectEmpty: "Projektnummer eingeben.",
    validationProjectFormat: "Die Projektnummer muss ПСД/48/2026/XXX oder ПСД/48/2026/XXX-SUFFIX entsprechen.",
    validationTu: "TU-Datei DOCX/PDF auswahlen.",
    validationPlan: "Plan-Datei DWG/DXF auswahlen.",
    processError: "Projekt konnte nicht verarbeitet werden.",
    unresolved: "Einige Platzhalter wurden nicht ersetzt:",
    checkLog: "Prufen Sie log.txt.",
    success: "Die Notiz wurde erstellt. Platzhalter wurden ersetzt.",
    pdfUnavailable: "PDF ist noch nicht verfugbar.",
    checkPanelOpen: "Prufen",
    checkPanelClose: "Schliessen",
    checkPanelEyebrow: "Vorprufung",
    checkPanelTitle: "Quelldateien prufen",
    checkPanelCopy: "Laden Sie TU, Plan und Notiz hoch. Das System pruft Daten, Stutzen und Platzhalter.",
    checkPanelReuse: "Dateien aus dem Hauptformular verwenden, wenn bereits gewahlt",
    checkNoteUpload: "Notiz DWG/DXF",
    checkPanelNoteHint: "Ohne Notiz wird die automatisch gewahlte Vorlage gepruft.",
    checkPanelRun: "Prufen",
    checkPanelRunning: "Prufung...",
    validationCheckTu: "TU-Datei fur die Prufung auswahlen.",
    validationCheckPlan: "Plan-Datei fur die Prufung auswahlen.",
    checkSummaryReady: "Keine kritischen Fehler gefunden.",
    checkSummaryWarningsOnly: "Keine kritischen Fehler. Warnungen: {warnings}.",
    checkSummaryIssues: "Fehler: {errors}, Warnungen: {warnings}.",
    checkCategoryTu: "TU",
    checkCategoryPlan: "Plan",
    checkCategoryNote: "Notiz",
    checkCategoryCross: "Quercheck",
    checkCategoryWire: "Leiter",
    checkCategoryProject: "Projekt",
    checkCategoryArmature: "Armatur",
    checkArmatureTitle: "Armaturberechnung nach Plan",
    checkSeverityError: "Fehler",
    checkSeverityWarning: "Warnung",
    checkSeverityInfo: "Info",
  },
  it: {
    brand: "Automazione TU",
    systemStatus: "Sistema per documentazione tecnica",
    languageLabel: "Lingua",
    themeLight: "Tema chiaro",
    themeDark: "Tema scuro",
    eyebrow: "Area tecnica locale",
    heroTitle: "Preparazione automatica della documentazione TU",
    heroCopy: "Carica TU e il piano DWG/DXF pronto, inserisci il numero di progetto e il sistema preparera la nota e il pacchetto PDF.",
    inputData: "Dati iniziali",
    idle: "In attesa",
    projectNumber: "Numero progetto",
    wirePanelEyebrow: "Parametro chiave",
    wirePanelTitle: "Scelta conduttore",
    wirePanelSubtitle: "Scegli la sezione manualmente o lascia il rilevamento automatico dal TU",
    wireModeAuto: "Auto",
    wireModeManual: "Manuale",
    wireAuto: "Automatico",
    wireAutoMeta: "Dalle condizioni tecniche",
    wireManualMeta: "Selezione manuale",
    uploadSection: "Carica file sorgente",
    wireHintAuto: "Il sistema rilevera il conduttore automaticamente",
    wireHintManual: "Selezionato manualmente: {wire}. Il rilevamento automatico verra sovrascritto.",
    wireResultAuto: "Rilevato automaticamente: {auto}. Conduttore finale: {final}.",
    wireResultManual: "Rilevato automaticamente: {auto}. Conduttore finale: {final}.",
    tuUpload: "TU DOCX/PDF",
    planUpload: "Piano DWG/DXF",
    noFile: "Nessun file selezionato",
    processingStatus: "Stato elaborazione",
    stepFiles: "File caricati",
    stepTu: "Dati TU estratti",
    stepPlan: "Piano analizzato",
    stepMap: "Mappa sostituzioni creata",
    stepDwg: "Nota compilata",
    stepDone: "Pronto",
    cardOneTitle: "Compila la nota",
    cardOneText: "Inserisci il numero, aggiungi TU e piano: il sistema prepara la nota DWG con i dati necessari.",
    cardTwoTitle: "Controlla il piano",
    cardTwoText: "L'app calcola lunghezza linea, sostegni e messa a terra senza modificare il disegno sorgente.",
    cardThreeTitle: "Crea il pacchetto",
    cardThreeText: "Dopo l'elaborazione puoi scaricare la nota e il PDF finale quando l'esportazione e disponibile.",
    footer: "Automazione TU — strumento tecnico per documentazione di progetto",
    dockStart: "Avvia",
    dockNote: "Scarica nota",
    dockPdf: "Scarica PDF",
    stateFiles: "Invio file",
    stateTu: "Lettura TU",
    statePlan: "Analisi piano",
    stateMap: "Creazione mappa",
    stateDwg: "Compilazione DWG",
    statePdf: "Creazione PDF",
    ready: "Pronto",
    check: "Controlla",
    error: "Errore",
    validationProjectEmpty: "Inserisci il numero di progetto.",
    validationProjectFormat: "Il numero deve seguire ПСД/48/2026/XXX o ПСД/48/2026/XXX-SUFFIX.",
    validationTu: "Scegli un file TU DOCX/PDF.",
    validationPlan: "Scegli un piano DWG/DXF.",
    processError: "Impossibile elaborare il progetto.",
    unresolved: "Alcuni placeholder non sono stati sostituiti:",
    checkLog: "Controlla log.txt.",
    success: "La nota e stata generata. Placeholder sostituiti.",
    pdfUnavailable: "PDF non ancora disponibile.",
    checkPanelOpen: "Controlla",
    checkPanelClose: "Chiudi",
    checkPanelEyebrow: "Controllo preliminare",
    checkPanelTitle: "Controllo file sorgente",
    checkPanelCopy: "Carica TU, piano e nota. Il sistema controlla dati, sostegni e placeholder.",
    checkPanelReuse: "Usa i file del modulo principale se gia selezionati",
    checkNoteUpload: "Nota DWG/DXF",
    checkPanelNoteHint: "Senza nota verra controllato il template selezionato automaticamente.",
    checkPanelRun: "Controlla",
    checkPanelRunning: "Controllo...",
    validationCheckTu: "Scegli un file TU per il controllo.",
    validationCheckPlan: "Scegli un piano per il controllo.",
    checkSummaryReady: "Nessun errore critico trovato.",
    checkSummaryWarningsOnly: "Nessun errore critico. Avvisi: {warnings}.",
    checkSummaryIssues: "Errori: {errors}, avvisi: {warnings}.",
    checkCategoryTu: "TU",
    checkCategoryPlan: "Piano",
    checkCategoryNote: "Nota",
    checkCategoryCross: "Incrocio",
    checkCategoryWire: "Conduttore",
    checkCategoryProject: "Progetto",
    checkCategoryArmature: "Armatura",
    checkArmatureTitle: "Calcolo armatura dal piano",
    checkSeverityError: "Errore",
    checkSeverityWarning: "Avviso",
    checkSeverityInfo: "Info",
  },
};

let currentLanguage = localStorage.getItem("tu-language") || "ru";
let currentTheme = localStorage.getItem("tu-theme") || "dark";
let progressTimer = null;
let progressIndex = 0;
let languageAnimationTimers = [];
let themeAnimationTimer = null;

const statusTimeline = [
  { step: "files_uploaded", stateKey: "stateFiles" },
  { step: "tu_extracted", stateKey: "stateTu" },
  { step: "plan_analyzed", stateKey: "statePlan" },
  { step: "replacement_map_created", stateKey: "stateMap" },
  { step: "dwg_filled", stateKey: "stateDwg" },
  { step: "completed", stateKey: "statePdf" },
];

let cursorFrame = 0;
let pendingCursorX = 0;
let pendingCursorY = 0;
window.addEventListener(
  "pointermove",
  (event) => {
    if (!cursorLight) return;
    pendingCursorX = event.clientX;
    pendingCursorY = event.clientY;
    if (cursorFrame) return;
    cursorFrame = window.requestAnimationFrame(() => {
      cursorFrame = 0;
      cursorLight.style.transform = `translate3d(${pendingCursorX}px, ${pendingCursorY}px, 0) translate(-50%, -50%)`;
    });
  },
  { passive: true },
);

liquidTargets.forEach((target) => {
  let frame = 0;
  let nextX = 0;
  let nextY = 0;
  target.addEventListener(
    "pointermove",
    (event) => {
      const rect = target.getBoundingClientRect();
      nextX = event.clientX - rect.left;
      nextY = event.clientY - rect.top;
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        target.style.setProperty("--mx", `${nextX}px`);
        target.style.setProperty("--my", `${nextY}px`);
      });
    },
    { passive: true },
  );
});

tuFile.addEventListener("change", () => updateFileName(tuFile, tuName));
planFile.addEventListener("change", () => updateFileName(planFile, planName));

wireTrigger.addEventListener("click", (event) => {
  event.stopPropagation();
  const willOpen = !wirePicker.classList.contains("is-open");
  setLanguageMenuOpen(false);
  setWireMenuOpen(willOpen);
});

wireOptions.forEach((option) => {
  option.addEventListener("click", () => {
    const nextValue = option.dataset.value;
    if (!nextValue || nextValue === currentWireValue) {
      setWireMenuOpen(false);
      return;
    }
    currentWireValue = nextValue;
    updateWirePickerUI();
    setWireMenuOpen(false);
    updateWireHint();
  });
});

function parseWireSelection() {
  const value = currentWireValue;
  if (value === "auto") {
    return { wire_selection_mode: "auto", wire_manual_value: "" };
  }
  if (value.startsWith("manual:")) {
    return {
      wire_selection_mode: "manual",
      wire_manual_value: value.slice("manual:".length),
    };
  }
  return { wire_selection_mode: "auto", wire_manual_value: "" };
}

function formatWireLabel(value) {
  return value.replace(/\*/g, "х").replace(/,/g, ",");
}

function syncWireFormFields() {
  const selection = parseWireSelection();
  wireSelectionMode.value = selection.wire_selection_mode;
  wireManualValue.value = selection.wire_manual_value || "";
}

function getWireOptionTitle(value) {
  const config = WIRE_OPTION_LABELS[value];
  if (!config) return value;
  if (config.titleKey) return t(config.titleKey);
  return config.title;
}

function updateWirePickerUI() {
  wireValue.textContent = getWireOptionTitle(currentWireValue);
  wireOptions.forEach((option) => {
    option.classList.toggle("is-active", option.dataset.value === currentWireValue);
  });
  wireMenu.querySelectorAll("[data-wire-label]").forEach((node) => {
    node.textContent = t(node.dataset.wireLabel);
  });
}

function setWireMenuOpen(isOpen) {
  const workspace = document.querySelector(".workspace");
  wirePicker.classList.toggle("is-open", isOpen);
  wireField.classList.toggle("is-picker-open", isOpen);
  form.classList.toggle("is-wire-picker-open", isOpen);
  workspace?.classList.toggle("is-wire-picker-open", isOpen);
  wireTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  wireMenu.hidden = !isOpen;
}

function updateWireHint() {
  syncWireFormFields();
  const selection = parseWireSelection();
  const isAuto = selection.wire_selection_mode === "auto";

  if (wireField) {
    wireField.classList.toggle("is-auto", isAuto);
    wireField.classList.toggle("is-manual", !isAuto);
  }

  if (isAuto) {
    wireHint.textContent = t("wireHintAuto");
    return;
  }

  wireHint.textContent = t("wireHintManual").replace(
    "{wire}",
    formatWireLabel(selection.wire_manual_value),
  );
}

function updateWireSelectLabels() {
  updateWirePickerUI();
}

function formatApiError(payload) {
  const detail = payload?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item.msg === "string") return item.msg;
        return JSON.stringify(item);
      })
      .join("; ");
  }
  return t("processError");
}

function formatWireSuccessNotice(payload) {
  const wire = payload?.wire;
  if (!wire) return "";
  const auto = wire.wire_auto_detected || "—";
  const finalWire = wire.wire_final_label || wire.wire_final_value || "—";
  return ` ${t("wireResultManual").replace("{auto}", auto).replace("{final}", finalWire)}`;
}

themeToggle.addEventListener("click", () => {
  currentTheme = currentTheme === "dark" ? "light" : "dark";
  localStorage.setItem("tu-theme", currentTheme);
  applyTheme(true);
});

languageTrigger.addEventListener("click", (event) => {
  event.stopPropagation();
  const willOpen = !languagePicker.classList.contains("is-open");
  setWireMenuOpen(false);
  setLanguageMenuOpen(willOpen);
});

languageOptions.forEach((option) => {
  option.addEventListener("click", () => {
    const nextLanguage = option.dataset.lang;
    if (!nextLanguage || nextLanguage === currentLanguage) {
      setLanguageMenuOpen(false);
      return;
    }
    currentLanguage = nextLanguage;
    localStorage.setItem("tu-language", currentLanguage);
    updateLanguagePickerUI();
    setLanguageMenuOpen(false);
    applyLanguage(true);
  });
});

document.addEventListener("click", (event) => {
  if (!languagePicker.contains(event.target)) {
    setLanguageMenuOpen(false);
  }
  if (!wirePicker.contains(event.target)) {
    setWireMenuOpen(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setLanguageMenuOpen(false);
    setWireMenuOpen(false);
    setCheckPanelOpen(false);
    setYopkPanelOpen(false);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice();

  const validation = validateForm();
  if (validation) {
    showNotice(validation, "error");
    return;
  }

  const jobProjectNumber = projectNumber.value.trim();
  const jobTuFile = tuFile.files[0];
  const jobPlanFile = planFile.files[0];
  syncWireFormFields();
  const jobWireMode = wireSelectionMode.value;
  const jobWireManual = wireManualValue.value;

  startButton.disabled = true;
  let runEntry = null;
  try {
    const detectBody = new FormData();
    detectBody.append("tu_file", jobTuFile);
    if (jobPlanFile) {
      detectBody.append("plan_file", jobPlanFile);
    }
    const detectResponse = await fetch("/api/detect", {
      method: "POST",
      body: detectBody,
    });
    const detectText = await detectResponse.text();
    let detectPayload = {};
    if (detectText) {
      detectPayload = JSON.parse(detectText);
    }
    if (!detectResponse.ok) {
      throw new Error(formatApiError(detectPayload));
    }

    let selectedBranchPoleType = branchPoleType.value.trim();
    if (detectPayload.requires_yopk) {
      selectedBranchPoleType = await askBranchPoleType();
      if (!selectedBranchPoleType) {
        runState.textContent = t("idle");
        return;
      }
      branchPoleType.value = selectedBranchPoleType;
    } else {
      branchPoleType.value = "";
      selectedBranchPoleType = "";
    }

    runEntry = {
      id: detectPayload.run_id || `local-${Date.now()}`,
      projectNumber: jobProjectNumber,
      status: "running",
      projectType: detectPayload.project_type || "",
      noteUrl: "",
      noteReady: false,
      error: "",
    };
    upsertProjectRun(runEntry);
    selectProjectRun(runEntry.id);
    startButton.disabled = false;

    await runProjectProcessing({
      runEntry,
      projectNumberValue: jobProjectNumber,
      tuFileValue: jobTuFile,
      planFileValue: jobPlanFile,
      wireMode: jobWireMode,
      wireManual: jobWireManual,
      selectedBranchPoleType,
      runId: detectPayload.run_id || "",
    });
  } catch (error) {
    const message =
      error?.name === "TypeError" || /load failed|failed to fetch/i.test(String(error?.message || ""))
        ? t("networkError")
        : error.message;
    if (runEntry) {
      runEntry.status = "error";
      runEntry.error = message;
      upsertProjectRun(runEntry);
    }
    stopProgressTimeline();
    runState.textContent = t("error");
    showNotice(message, "error");
  } finally {
    startButton.disabled = false;
  }
});

async function runProjectProcessing({
  runEntry,
  projectNumberValue,
  tuFileValue,
  planFileValue,
  wireMode,
  wireManual,
  selectedBranchPoleType,
  runId,
}) {
  const body = new FormData();
  body.set("project_number", projectNumberValue);
  body.append("tu_file", tuFileValue);
  body.append("plan_file", planFileValue);
  body.set("wire_selection_mode", wireMode || "auto");
  if (wireManual) {
    body.set("wire_manual_value", wireManual);
  }
  if (selectedBranchPoleType) {
    body.set("branch_pole_type", selectedBranchPoleType);
  }
  if (runId) {
    body.set("run_id", runId);
  }

  activeJobsCount += 1;
  resetStatus();
  startProgressTimeline();
  showNotice(t("processingStarted"), "success");

  let sessionId = runId || runEntry.id;
  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body,
    });
    const responseText = await response.text();
    let payload = {};
    if (responseText) {
      try {
        payload = JSON.parse(responseText);
      } catch {
        throw new Error(responseText.slice(0, 300) || t("processError"));
      }
    }

    if (!response.ok) {
      throw new Error(formatApiError(payload));
    }

    sessionId = payload.run_id || sessionId;
    runEntry.id = sessionId;
    runEntry.noteUrl = payload.note_download_url || `/api/download/${sessionId}/note`;
    runEntry.status = "running";
    runEntry.error = "";
    upsertProjectRun(runEntry);
    selectProjectRun(sessionId);

    if (payload.status === "processing") {
      payload = await pollRunStatus(sessionId, runEntry);
    }

    if (activeJobsCount <= 1) {
      stopProgressTimeline();
      applySteps(payload.steps);
    }

    const unresolved = payload.cad?.unresolved_placeholders || [];
    const warningText = payload.warnings?.length ? ` ${payload.warnings.join(" ")}` : "";
    const noteReady =
      Boolean(payload.success) &&
      (Boolean(payload.files?.note_result) ||
        payload.status === "completed" ||
        payload.status === "completed_with_warnings");

    runEntry.id = sessionId;
    runEntry.projectType = payload.project_type || runEntry.projectType;
    runEntry.noteUrl = payload.note_download_url || `/api/download/${sessionId}/note`;
    runEntry.noteReady = noteReady;
    runEntry.status = noteReady ? "ready" : "error";
    runEntry.error = noteReady
      ? ""
      : payload.message || payload.detail || `${t("unresolved")} ${(unresolved || []).join(", ")}. ${t("checkLog")}`;
    upsertProjectRun(runEntry);
    selectProjectRun(sessionId);

    if (!noteReady) {
      runState.textContent = t("check");
      showNotice(runEntry.error + warningText, "error");
      return;
    }

    runState.textContent = t("ready");
    const successMessage =
      payload.project_type === "10kv" ? t("success10kv") : t("success");
    const unresolvedNote = unresolved.length
      ? ` ${t("unresolved")} ${unresolved.join(", ")}.`
      : "";
    showNotice(
      `${successMessage}${unresolvedNote}${formatWireSuccessNotice(payload)}${warningText}`,
      "success",
    );
  } catch (error) {
    // Если соединение оборвалось, но сервер уже доделал записку — восстанавливаем статус.
    if (sessionId) {
      try {
        const recovered = await fetchRunStatus(sessionId);
        if (
          recovered &&
          (recovered.status === "completed" || recovered.status === "completed_with_warnings") &&
          recovered.success
        ) {
          runEntry.id = sessionId;
          runEntry.projectType = recovered.project_type || runEntry.projectType;
          runEntry.noteUrl = recovered.note_download_url || `/api/download/${sessionId}/note`;
          runEntry.noteReady = true;
          runEntry.status = "ready";
          runEntry.error = "";
          upsertProjectRun(runEntry);
          selectProjectRun(sessionId);
          if (activeJobsCount <= 1) {
            stopProgressTimeline();
            applySteps(recovered.steps);
          }
          runState.textContent = t("ready");
          showNotice(
            recovered.project_type === "10kv" ? t("success10kv") : t("success"),
            "success",
          );
          return;
        }
      } catch {
        // ignore recovery errors
      }
    }
    runEntry.status = "error";
    runEntry.error = error.message;
    upsertProjectRun(runEntry);
    throw error;
  } finally {
    activeJobsCount = Math.max(0, activeJobsCount - 1);
    if (activeJobsCount === 0) {
      stopProgressTimeline();
    }
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchRunStatus(runId) {
  const response = await fetch(`/api/status/${encodeURIComponent(runId)}`);
  const responseText = await response.text();
  let payload = {};
  if (responseText) {
    try {
      payload = JSON.parse(responseText);
    } catch {
      throw new Error(responseText.slice(0, 300) || t("processError"));
    }
  }
  if (!response.ok) {
    throw new Error(formatApiError(payload));
  }
  return payload;
}

async function pollRunStatus(runId, runEntry) {
  const started = Date.now();
  const maxMs = 20 * 60 * 1000;
  let lastPayload = null;

  while (Date.now() - started < maxMs) {
    const payload = await fetchRunStatus(runId);
    lastPayload = payload;

    runEntry.id = runId;
    runEntry.projectType = payload.project_type || runEntry.projectType;
    runEntry.noteUrl = payload.note_download_url || `/api/download/${runId}/note`;
    runEntry.status = "running";
    upsertProjectRun(runEntry);

    if (activeJobsCount <= 1 && payload.steps) {
      applySteps(payload.steps);
    }
    if (payload.message) {
      showNotice(payload.message, "success");
    }

    if (
      payload.status === "completed" ||
      payload.status === "completed_with_warnings" ||
      payload.status === "failed"
    ) {
      return payload;
    }

    await sleep(2000);
  }

  if (lastPayload && _noteLooksReady(lastPayload)) {
    return lastPayload;
  }
  throw new Error(t("networkError"));
}

function _noteLooksReady(payload) {
  return (
    Boolean(payload?.success) &&
    (payload.status === "completed" ||
      payload.status === "completed_with_warnings" ||
      Boolean(payload.files?.note_result))
  );
}

addParallelProject?.addEventListener("click", () => {
  prepareParallelProjectForm();
});

function prepareParallelProjectForm() {
  projectNumber.value = "";
  tuFile.value = "";
  planFile.value = "";
  updateFileName(tuFile, tuName);
  updateFileName(planFile, planName);
  branchPoleType.value = "";
  currentWireValue = "auto";
  updateWirePickerUI();
  syncWireFormFields();
  updateWireHint();
  clearNotice();
  if (activeJobsCount === 0) {
    resetStatus();
  }
  showNotice(t("parallelFormReady"), "success");
  projectNumber.focus();
}

function upsertProjectRun(entry) {
  const index = projectRuns.findIndex((item) => item.id === entry.id);
  if (index >= 0) {
    projectRuns[index] = entry;
  } else {
    projectRuns.unshift(entry);
  }
  renderProjectRuns();
}

function selectProjectRun(runId) {
  const entry = projectRuns.find((item) => item.id === runId);
  if (!entry) return;
  selectedRunId = runId;
  lastNoteDownloadUrl = entry.noteUrl || `/api/download/${runId}/note`;
  setDownloads(Boolean(entry.noteReady));
  renderProjectRuns();
}

function ensureProjectsListDelegation() {
  if (!projectsList || projectsListBound) return;
  projectsListBound = true;
  projectsList.addEventListener("click", (event) => {
    const actionButton = event.target?.closest?.("[data-action]");
    const card = event.target?.closest?.(".project-run");
    if (!card) return;
    const runId = card.dataset.runId;
    if (actionButton?.dataset?.action === "note") {
      event.preventDefault();
      downloadProjectNote(runId);
      return;
    }
    selectProjectRun(runId);
  });
}

function renderProjectRuns() {
  if (!projectsList || !projectsCount) return;
  ensureProjectsListDelegation();
  projectsCount.textContent = String(projectRuns.length);
  if (!projectRuns.length) {
    projectsList.innerHTML = "";
    return;
  }

  projectsList.innerHTML = projectRuns
    .map((entry) => {
      const typeLabel =
        entry.projectType === "10kv" ? t("projectType10") : t("projectType04");
      const statusLabel =
        entry.status === "ready"
          ? t("projectReady")
          : entry.status === "error"
            ? t("projectFailed")
            : t("projectRunning");
      const meta =
        entry.status === "error" && entry.error
          ? entry.error
          : `${typeLabel} · ${statusLabel}`;
      return `
        <article class="project-run ${entry.id === selectedRunId ? "is-selected" : ""} ${
          entry.status === "running" ? "is-running" : ""
        } ${entry.status === "error" ? "is-error" : ""}" data-run-id="${entry.id}">
          <div class="project-run__title">${escapeHtml(entry.projectNumber)}</div>
          <div class="project-run__meta">${escapeHtml(meta)}</div>
          <div class="project-run__actions">
            <button type="button" data-action="note" ${entry.noteReady ? "" : "disabled"}>
              ${t("projectDownloadNote")}
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

function downloadProjectNote(runId) {
  const entry = projectRuns.find((item) => item.id === runId);
  if (!entry?.noteReady) return;
  selectProjectRun(runId);
  window.location.href = entry.noteUrl;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setYopkPanelOpen(isOpen) {
  document.body.classList.toggle("is-yopk-panel-open", isOpen);
  if (yopkPanel) {
    yopkPanel.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }
  if (yopkBackdrop) {
    yopkBackdrop.hidden = !isOpen;
  }
}

function askBranchPoleType() {
  return new Promise((resolve) => {
    setYopkPanelOpen(true);

    const cleanup = (value) => {
      setYopkPanelOpen(false);
      yopkIntermediate.removeEventListener("click", onIntermediate);
      yopkAnchor.removeEventListener("click", onAnchor);
      yopkBackdrop.removeEventListener("click", onCancel);
      resolve(value);
    };

    const onIntermediate = () => cleanup("intermediate");
    const onAnchor = () => cleanup("anchor");
    const onCancel = () => cleanup("");

    yopkIntermediate.addEventListener("click", onIntermediate);
    yopkAnchor.addEventListener("click", onAnchor);
    yopkBackdrop.addEventListener("click", onCancel);
  });
}

downloadNote?.addEventListener("click", () => {
  if (selectedRunId) {
    downloadProjectNote(selectedRunId);
    return;
  }
  window.location.href = lastNoteDownloadUrl;
});

if (downloadPdf) {
  downloadPdf.hidden = true;
  downloadPdf.disabled = true;
}

function setCheckPanelOpen(isOpen) {
  document.body.classList.toggle("is-check-panel-open", isOpen);
  if (checkPanel) {
    checkPanel.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }
  if (checkPanelBackdrop) {
    checkPanelBackdrop.hidden = !isOpen;
  }
}

function resolveCheckFile(mainInput, panelInput) {
  if (useMainFormFiles?.checked && mainInput?.files?.length) {
    return mainInput.files[0];
  }
  return panelInput?.files?.[0] || null;
}

function validateCheckForm() {
  const tu = resolveCheckFile(tuFile, checkTuFile);
  const plan = resolveCheckFile(planFile, checkPlanFile);
  if (!tu) return t("validationCheckTu");
  if (!plan) return t("validationCheckPlan");
  return "";
}

function renderCheckResults(payload) {
  if (!checkResults || !checkSummary || !checkIssueList) return;

  const blocking = payload?.blocking_count || 0;
  const warnings = payload?.warning_count || 0;
  const isReady = payload?.ready === true;
  const isFullyClean = isReady && warnings === 0;

  checkSummary.className = `check-panel__summary ${isFullyClean ? "is-ready" : "is-issues"}`;
  if (isFullyClean) {
    checkSummary.textContent = t("checkSummaryReady");
  } else if (isReady && warnings > 0) {
    checkSummary.textContent = t("checkSummaryWarningsOnly").replace("{warnings}", String(warnings));
  } else {
    checkSummary.textContent = t("checkSummaryIssues").replace("{errors}", String(blocking)).replace("{warnings}", String(warnings));
  }

  if (checkArmature) {
    checkArmature.hidden = true;
  }

  checkIssueList.replaceChildren();
  if (isFullyClean) {
    checkIssueList.hidden = true;
    checkResults.hidden = false;
    return;
  }

  checkIssueList.hidden = false;
  const issues = payload?.issues || [];
  issues.forEach((issue) => {
    const item = document.createElement("li");
    item.className = `check-issue is-${issue.severity}`;
    const categoryKey = `checkCategory${(issue.category || "").charAt(0).toUpperCase()}${(issue.category || "").slice(1)}`;
    const severityKey = `checkSeverity${(issue.severity || "info").charAt(0).toUpperCase()}${(issue.severity || "info").slice(1)}`;
    const locationHtml = issue.location
      ? `<span class="check-issue__location">${issue.location}</span>`
      : "";
    item.innerHTML = `
      <span class="check-issue__badge">${t(severityKey)}</span>
      <div class="check-issue__body">
        <span class="check-issue__category">${t(categoryKey)}</span>
        ${locationHtml}
        <p class="check-issue__message">${issue.message}</p>
      </div>
    `;
    checkIssueList.appendChild(item);
  });

  checkResults.hidden = false;
}

openCheckPanel?.addEventListener("click", () => {
  setLanguageMenuOpen(false);
  setWireMenuOpen(false);
  setCheckPanelOpen(true);
});

closeCheckPanel?.addEventListener("click", () => setCheckPanelOpen(false));
checkPanelBackdrop?.addEventListener("click", () => setCheckPanelOpen(false));

[checkTuFile, checkPlanFile, checkNoteFile].forEach((input) => {
  if (!input) return;
  input.addEventListener("change", () => {
    const targetMap = {
      checkTuFile: checkTuName,
      checkPlanFile: checkPlanName,
      checkNoteFile: checkNoteName,
    };
    updateFileName(input, targetMap[input.id]);
  });
});

checkForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const validation = validateCheckForm();
  if (validation) {
    checkSummary.className = "check-panel__summary is-issues";
    checkSummary.textContent = validation;
    checkResults.hidden = false;
    checkIssueList.replaceChildren();
    return;
  }

  const body = new FormData();
  body.append("tu_file", resolveCheckFile(tuFile, checkTuFile));
  body.append("plan_file", resolveCheckFile(planFile, checkPlanFile));
  const note = resolveCheckFile(null, checkNoteFile);
  if (note) {
    body.append("note_file", note);
  }
  const projectValue = projectNumber.value.trim();
  if (projectValue) {
    body.append("project_number", projectValue);
  }
  syncWireFormFields();
  body.append("wire_selection_mode", wireSelectionMode.value);
  if (wireManualValue.value) {
    body.append("wire_manual_value", wireManualValue.value);
  }

  runCheckButton.disabled = true;
  runCheckButton.textContent = t("checkPanelRunning");
  checkResults.hidden = false;
  checkSummary.className = "check-panel__summary";
  checkSummary.textContent = t("checkPanelRunning");
  checkIssueList.replaceChildren();

  try {
    const response = await fetch("/api/validate", {
      method: "POST",
      body,
    });
    const responseText = await response.text();
    let payload = {};
    if (responseText) {
      try {
        payload = JSON.parse(responseText);
      } catch {
        throw new Error(responseText.slice(0, 300) || t("processError"));
      }
    }
    if (!response.ok) {
      throw new Error(formatApiError(payload));
    }
    renderCheckResults(payload);
  } catch (error) {
    checkSummary.className = "check-panel__summary is-issues";
    checkSummary.textContent = error.message;
    checkIssueList.replaceChildren();
  } finally {
    runCheckButton.disabled = false;
    runCheckButton.textContent = t("checkPanelRun");
  }
});

applyTheme(false);
updateLanguagePickerUI();
updateWirePickerUI();
applyLanguage(false);
updateWireHint();
resetStatus();

function setLanguageMenuOpen(isOpen) {
  languagePicker.classList.toggle("is-open", isOpen);
  languageTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  languageMenu.hidden = !isOpen;
}

function updateLanguagePickerUI() {
  if (!translations[currentLanguage]) currentLanguage = "ru";
  const meta = LANGUAGE_META[currentLanguage] || LANGUAGE_META.ru;
  languageFlag.textContent = meta.flag;
  languageName.textContent = meta.name;
  languageOptions.forEach((option) => {
    option.classList.toggle("is-active", option.dataset.lang === currentLanguage);
  });
}

function t(key) {
  return translations[currentLanguage]?.[key] || translations.ru[key] || key;
}

function applyLanguage(animated = false) {
  clearLanguageAnimationTimers();

  const updateLanguage = (visibleText = true) => {
    if (!translations[currentLanguage]) currentLanguage = "ru";
    document.documentElement.lang = currentLanguage;
    document.title = t("brand");
    updateLanguagePickerUI();

    if (visibleText) {
      collectLanguageTargets().forEach(({ node, text }) => {
        node.textContent = text;
      });
    }
    document.querySelectorAll("[data-i18n-label]").forEach((node) => {
      node.dataset.label = t(node.dataset.i18nLabel);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
      node.setAttribute("aria-label", t(node.dataset.i18nAria));
    });

    if (visibleText) {
      updateFileName(tuFile, tuName);
      updateFileName(planFile, planName);
      updateFileName(checkTuFile, checkTuName);
      updateFileName(checkPlanFile, checkPlanName);
      updateFileName(checkNoteFile, checkNoteName);
      updateWirePickerUI();
      updateWireHint();
      renderProjectRuns();
      if (!progressTimer) {
        runState.textContent = t("idle");
      } else {
        advanceProgress();
      }
    }
  };

  if (!animated) {
    updateLanguage();
    return;
  }

  const targets = collectLanguageTargets();
  updateLanguage(false);
  document.body.classList.add("is-language-swapping");

  const animatedTargets = targets.filter(({ node, text }) => node.textContent !== text);
  const totalUnits = animatedTargets.reduce((sum, { node, text }) => {
    return sum + Math.max(splitLanguageWords(node.textContent).length, splitLanguageWords(text).length, 1);
  }, 0);

  if (!totalUnits) {
    updateLanguage();
    document.body.classList.remove("is-language-swapping");
    return;
  }

  const stepMs = Math.min(58, Math.max(4, 1450 / totalUnits));
  let sequenceIndex = 0;

  animatedTargets.forEach(({ node, text }) => {
    const oldWords = splitLanguageWords(node.textContent);
    const newWords = splitLanguageWords(text);
    const wordCount = Math.max(oldWords.length, newWords.length, 1);
    const fragment = document.createDocumentFragment();
    const spans = [];

    for (let index = 0; index < wordCount; index += 1) {
      const span = document.createElement("span");
      span.className = "language-word";
      span.textContent = oldWords[index] || "";
      spans.push(span);
      fragment.appendChild(span);
    }

    node.replaceChildren(fragment);

    spans.forEach((span, index) => {
      const delay = Math.floor(sequenceIndex * stepMs);
      sequenceIndex += 1;
      const timer = window.setTimeout(() => {
        span.classList.add("is-changing");
        const swapTimer = window.setTimeout(() => {
          span.textContent = newWords[index] || "";
          span.classList.remove("is-changing");
          span.classList.add("is-arriving");
          const arriveTimer = window.setTimeout(() => {
            span.classList.remove("is-arriving");
          }, 430);
          languageAnimationTimers.push(arriveTimer);
        }, 135);
        languageAnimationTimers.push(swapTimer);
      }, delay);
      languageAnimationTimers.push(timer);
    });
  });

  const finishDelay = Math.min(1950, Math.ceil(sequenceIndex * stepMs + 500));
  const finishTimer = window.setTimeout(() => {
    updateLanguage();
    document.body.classList.remove("is-language-swapping");
    languageAnimationTimers = [];
  }, finishDelay);
  languageAnimationTimers.push(finishTimer);
}

function clearLanguageAnimationTimers() {
  languageAnimationTimers.forEach((timer) => window.clearTimeout(timer));
  languageAnimationTimers = [];
  document.body.classList.remove("is-language-swapping");
}

function collectLanguageTargets() {
  return [...document.querySelectorAll("[data-i18n]")].map((node) => {
    let key = node.dataset.i18n;
    if (node === themeToggle) {
      key = currentTheme === "dark" ? "themeLight" : "themeDark";
    }
    if (node === runState && progressTimer) {
      key = statusTimeline[Math.min(progressIndex, statusTimeline.length - 1)]?.stateKey || "idle";
    }
    return { node, text: t(key) };
  });
}

function splitLanguageWords(text) {
  return text.match(/\S+\s*/g) || (text ? [text] : [""]);
}

function applyTheme(animated = false) {
  if (themeAnimationTimer) {
    window.clearTimeout(themeAnimationTimer);
    themeAnimationTimer = null;
  }
  if (animated) {
    document.body.classList.add("is-theme-swapping");
    themeAnimationTimer = window.setTimeout(() => {
      document.body.classList.remove("is-theme-swapping");
      themeAnimationTimer = null;
    }, 1300);
  }
  document.body.dataset.theme = currentTheme;
  themeToggle.textContent = currentTheme === "dark" ? t("themeLight") : t("themeDark");
}

function updateFileName(input, target) {
  const fileName = input.files[0]?.name;
  const uploadControl = input.closest(".upload-control");
  target.textContent = fileName || t("noFile");
  target.dataset.empty = fileName ? "false" : "true";
  if (uploadControl) {
    uploadControl.dataset.empty = fileName ? "false" : "true";
  }
}

function validateForm() {
  const value = projectNumber.value.trim();
  if (!value) {
    return t("validationProjectEmpty");
  }
  if (!projectNumberPattern.test(value)) {
    return t("validationProjectFormat");
  }
  if (!tuFile.files.length) {
    return t("validationTu");
  }
  if (!planFile.files.length) {
    return t("validationPlan");
  }
  return "";
}

function setStep(step, done) {
  const item = statusItems.find((node) => node.dataset.step === step);
  if (!item) return;
  item.classList.toggle("is-done", done);
  if (done) {
    item.classList.remove("is-active");
  }
}

function setActiveStep(step) {
  statusItems.forEach((item) => item.classList.remove("is-active"));
  const item = statusItems.find((node) => node.dataset.step === step);
  if (!item || item.classList.contains("is-done")) return;
  item.classList.add("is-active");
}

function applySteps(steps = {}) {
  statusTimeline.forEach(({ step }) => setStep(step, steps?.[step] === true));
}

function startProgressTimeline() {
  stopProgressTimeline();
  progressIndex = 0;
  advanceProgress();
  progressTimer = window.setInterval(() => {
    if (progressIndex >= statusTimeline.length - 1) return;
    progressIndex += 1;
    advanceProgress();
  }, 1900);
}

function advanceProgress() {
  const current = statusTimeline[progressIndex];
  if (!current) return;
  runState.textContent = t(current.stateKey);
  setActiveStep(current.step);
}

function stopProgressTimeline() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
  statusItems.forEach((item) => item.classList.remove("is-active"));
}

function resetStatus() {
  stopProgressTimeline();
  statusItems.forEach((item) => item.classList.remove("is-done", "is-active"));
  runState.textContent = t("idle");
}

function setDownloads(enabled) {
  if (downloadNote) {
    downloadNote.disabled = !enabled;
  }
  if (!enabled && !selectedRunId) {
    lastNoteDownloadUrl = "/api/download/note";
  }
}

function showNotice(message, type) {
  notice.textContent = message;
  notice.className = `notice is-visible is-${type}`;
}

function clearNotice() {
  notice.textContent = "";
  notice.className = "notice";
}
