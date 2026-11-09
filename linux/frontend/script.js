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
const statusProgressBar = document.querySelector("#statusProgressBar");
const statusProgressValue = document.querySelector("#statusProgressValue");
const cursorLight = document.querySelector("#cursorLight");
const themeToggle = document.querySelector("#themeToggle");
const settingsMenu = document.querySelector("#settingsMenu");
const settingsTrigger = document.querySelector("#settingsTrigger");
const settingsPanel = document.querySelector("#settingsPanel");
const languagePicker = document.querySelector("#languagePicker");
const languageTrigger = document.querySelector("#languageTrigger");
const languageMenu = document.querySelector("#languageMenu");
const languageFlag = document.querySelector("#languageFlag");
const languageName = document.querySelector("#languageName");
const languageOptions = [...document.querySelectorAll("#languageMenu .language-picker__option")];
const liveStatusPanel = document.querySelector("#liveStatusPanel");
const statusIdleHint = document.querySelector("#statusIdleHint");
const projectsPanel = document.querySelector("#projectsPanel");
const benefitCards = [...document.querySelectorAll(".benefit-card[data-stage]")];
const workspaceRoot = document.querySelector("#workspaceRoot");
const workspaceTabs = [...document.querySelectorAll("[data-workspace-tab]")];
const openAiEngineerTab = document.querySelector("#openAiEngineerTab");
const aiEngineerTabButton = document.querySelector("#aiEngineerTabButton");
const aiEngineerPanel = document.querySelector("#aiEngineerPanel");
const aiEngineerIdle = document.querySelector("#aiEngineerIdle");
const aiEngineerReport = document.querySelector("#aiEngineerReport");
const aiEngineerScore = document.querySelector("#aiEngineerScore");
const aiEngineerSummary = document.querySelector("#aiEngineerSummary");
const aiEngineerChecked = document.querySelector("#aiEngineerChecked");
const aiEngineerPlacement = document.querySelector("#aiEngineerPlacement");
const aiEngineerFindings = document.querySelector("#aiEngineerFindings");
const aiEngineerFindingsCount = document.querySelector("#aiEngineerFindingsCount");
const aiEngineerDisclaimer = document.querySelector("#aiEngineerDisclaimer");
const aiEngineerModeBadge = document.querySelector("#aiEngineerModeBadge");
const aiEngineerChat = document.querySelector("#aiEngineerChat");
const aiEngineerChatLog = document.querySelector("#aiEngineerChatLog");
const aiEngineerChatForm = document.querySelector("#aiEngineerChatForm");
const aiEngineerChatInput = document.querySelector("#aiEngineerChatInput");
const aiEngineerChatSend = document.querySelector("#aiEngineerChatSend");
const aiEngineerChatStatus = document.querySelector("#aiEngineerChatStatus");
const aiEngineerChatTyping = document.querySelector("#aiEngineerChatTyping");
let aiChatRunId = "";
let aiChatBusy = false;
let aiChatHasProject = false;
let aiReportFetchSeq = 0;
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
    themeLabel: "Тема",
    settingsOpen: "Настройки",
    settingsTitle: "Настройки",
    themeLight: "Светлая тема",
    themeDark: "Темная тема",
    statusIdleTitle: "Очередь и прогресс",
    statusIdleText: "После запуска здесь появится ход обработки и список проектов.",
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
    stepTu: "ТУ проанализированы",
    stepPlan: "Анализ плана",
    stepMap: "Создание карты замен",
    stepDwg: "Генерация записки",
    stepDone: "Готово",
    cardOneTitle: "Определяет тип проекта",
    cardOneText: "Сама понимает, это 0,4 кВ или 10 кВ: читает ТУ и план, выбирает нужный шаблон записки.",
    cardTwoTitle: "Читает готовый план",
    cardTwoText: "Считает длину линии, опоры и заземления. Чертёж не меняет — только извлекает данные.",
    cardThreeTitle: "Собирает записку",
    cardThreeText: "Подставляет номер проекта, данные из ТУ и расчёты в копию шаблона и отдаёт файл на скачивание.",
    tabProject: "Проект",
    aiEngineerTab: "AI Engineer",
    aiEngineerEyebrow: "Пост-проверка готового проекта",
    aiEngineerTitle: "AI Engineer",
    aiEngineerIdleTitle: "Отчёт появится после генерации",
    aiEngineerIdleText:
      "Сначала сформируйте проект на вкладке «Проект». AI Engineer не меняет файлы — только даёт рекомендации.",
    aiEngineerScoreLabel: "Общий рейтинг проекта",
    aiEngineerCheckedTitle: "Что проверено",
    aiEngineerFindingsTitle: "Замечания",
    aiEngineerDisclaimer:
      "Все замечания — рекомендации. AI Engineer не изменяет проект автоматически.",
    aiEngineerNoFindings: "Замечаний нет",
    aiEngineerOneFinding: "1 рекомендация",
    aiEngineerManyFindings: "{count} рекомендаций",
    aiEngineerCriticalNone: "🟢 Критических замечаний нет",
    aiEngineerModeRules: "Правила",
    aiEngineerModeLlm: "Правила + LLM",
    aiEngineerViewAction: "Почему?",
    aiEngineerHideAction: "Скрыть",
    aiEngineerFixAction: "Как решить?",
    aiEngineerHideFixAction: "Скрыть решение",
    aiEngineerChatTitle: "Инженер в чате",
    aiEngineerChatLive: "Онлайн · знает этот проект",
    aiEngineerChatStandby: "Онлайн · нормы и правила",
    aiEngineerChatGhostUser: "Сколько F207 на А23?",
    aiEngineerChatGhostBot: "Можно спрашивать и без проекта: нормы, арматура, ПП23. Когда записка готова — разберём замечания по вашему плану.",
    aiEngineerChatHint:
      "Спросите по нормам ВЛ или по этому проекту. Проект не обязателен — Luna отвечает и без него.",
    aiEngineerChatPlaceholder: "Спросите по нормам или по проекту…",
    aiEngineerChatSend: "Спросить",
    aiEngineerChatWait: "Думаю…",
    aiEngineerChatEmpty: "Задайте вопрос — например, чем ПП23 отличается от П23.",
    aiEngineerChatYou: "Вы",
    aiEngineerChatBot: "AI Engineer",
    aiEngineerChatNeedProject: "Сначала сформируйте проект.",
    aiEngineerChatError: "Не удалось получить ответ. Проверьте, что программа запущена, и спросите ещё раз.",
    aiEngineerGeometryAlert: "AI Engineer: опоры/заземления не на полилинии 0,4 кВ",
    aiEngineerCardAlert: "AI: исправить план",
    footer: "Автоматизация ТУ — инженерный инструмент для подготовки проектной документации",
    dockStart: "Старт",
    dockNote: "Скачать записку",
    dockPdf: "Скачать PDF",
    addParallelProject: "Параллельный проект",
    projectsListTitle: "Очередь проектов",
    projectsListHint: "Локальный сервер: проекты идут параллельно, у каждого свой прогресс и скачивание.",
    parallelFormReady: "Форма очищена. Загрузите ТУ и план для следующего проекта — предыдущие скачивания сохранятся.",
    projectRunning: "Обрабатывается…",
    projectReady: "Готов к скачиванию",
    projectFailed: "Ошибка",
    projectCardTitle: "Проект {code}",
    projectStageReady: "Готов",
    projectStageFailed: "Ошибка",
    projectStageRunning: "Обработка…",
    projectDownloadNote: "Скачать",
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
    themeLabel: "Theme",
    settingsOpen: "Settings",
    settingsTitle: "Settings",
    themeLight: "Light theme",
    themeDark: "Dark theme",
    statusIdleTitle: "Queue and progress",
    statusIdleText: "After you start, processing progress and the project list appear here.",
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
    stepTu: "TU analyzed",
    stepPlan: "Plan analysis",
    stepMap: "Replacement map",
    stepDwg: "Note generation",
    stepDone: "Done",
    cardOneTitle: "Detects project type",
    cardOneText: "Automatically tells 0.4 kV from 10 kV using the TU and plan, then picks the matching note template.",
    cardTwoTitle: "Reads the finished plan",
    cardTwoText: "Counts line length, supports, and grounding. The drawing stays unchanged — data only.",
    cardThreeTitle: "Builds the note",
    cardThreeText: "Fills a template copy with the project number, TU data, and calculations, then offers the file for download.",
    tabProject: "Project",
    aiEngineerTab: "AI Engineer",
    aiEngineerEyebrow: "Post-check of the finished project",
    aiEngineerTitle: "AI Engineer",
    aiEngineerIdleTitle: "Report appears after generation",
    aiEngineerIdleText:
      "Generate a project on the Project tab first. AI Engineer never changes files — it only recommends reviews.",
    aiEngineerScoreLabel: "Overall project rating",
    aiEngineerCheckedTitle: "Checked",
    aiEngineerFindingsTitle: "Findings",
    aiEngineerDisclaimer: "All findings are recommendations. AI Engineer never modifies the project.",
    aiEngineerNoFindings: "No findings",
    aiEngineerOneFinding: "1 recommendation",
    aiEngineerManyFindings: "{count} recommendations",
    aiEngineerCriticalNone: "🟢 No critical findings",
    aiEngineerModeRules: "Rules",
    aiEngineerModeLlm: "Rules + LLM",
    aiEngineerViewAction: "Why?",
    aiEngineerHideAction: "Hide",
    aiEngineerFixAction: "How to fix?",
    aiEngineerHideFixAction: "Hide fix",
    aiEngineerChatTitle: "Engineer on chat",
    aiEngineerChatLive: "Online · knows this project",
    aiEngineerChatStandby: "Online · norms and rules",
    aiEngineerChatGhostUser: "How many F207 on A23?",
    aiEngineerChatGhostBot: "You can ask without a project: norms, hardware, PP23. After the note is built, we’ll go through findings on your plan.",
    aiEngineerChatHint: "Ask about VL norms or this project. A project is optional — Luna answers either way.",
    aiEngineerChatPlaceholder: "Ask about norms or this project…",
    aiEngineerChatSend: "Ask",
    aiEngineerChatWait: "Thinking…",
    aiEngineerChatEmpty: "Ask a question — for example, how PP23 differs from P23.",
    aiEngineerChatYou: "You",
    aiEngineerChatBot: "AI Engineer",
    aiEngineerChatNeedProject: "Generate a project first.",
    aiEngineerChatError: "Could not get a reply.",
    aiEngineerGeometryAlert: "AI Engineer: supports/groundings are off the 0.4 kV polyline",
    aiEngineerCardAlert: "AI: fix the plan",
    footer: "TU Automation — an engineering tool for project documentation",
    dockStart: "Start",
    dockNote: "Download note",
    dockPdf: "Download PDF",
    addParallelProject: "Parallel project",
    projectsListTitle: "Project queue",
    projectsListHint: "Local server feel: projects run in parallel with their own progress and downloads.",
    parallelFormReady: "Form cleared. Upload TU and plan for the next project — previous downloads stay available.",
    projectRunning: "Processing…",
    projectReady: "Ready to download",
    projectFailed: "Error",
    projectCardTitle: "Project {code}",
    projectStageReady: "Ready",
    projectStageFailed: "Error",
    projectStageRunning: "Processing…",
    projectDownloadNote: "Download",
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
    themeLabel: "Thema",
    settingsOpen: "Einstellungen",
    settingsTitle: "Einstellungen",
    themeLight: "Helles Design",
    themeDark: "Dunkles Design",
    statusIdleTitle: "Warteschlange und Fortschritt",
    statusIdleText: "Nach dem Start erscheinen hier der Fortschritt und die Projektliste.",
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
    stepTu: "TU analysiert",
    stepPlan: "Plananalyse",
    stepMap: "Ersetzungskarte",
    stepDwg: "Notiz erzeugen",
    stepDone: "Fertig",
    cardOneTitle: "Erkennt den Projekttyp",
    cardOneText: "Unterscheidet selbst 0,4 kV und 10 kV anhand von TU und Plan und wählt die passende Notiz-Vorlage.",
    cardTwoTitle: "Liest den fertigen Plan",
    cardTwoText: "Zählt Leitungslänge, Stützen und Erdungen. Die Zeichnung bleibt unverändert — nur Daten.",
    cardThreeTitle: "Erstellt die Notiz",
    cardThreeText: "Füllt eine Vorlagenkopie mit Projektnummer, TU-Daten und Berechnungen und stellt die Datei zum Download bereit.",
    tabProject: "Projekt",
    aiEngineerTab: "AI Engineer",
    aiEngineerEyebrow: "Nachprufung des fertigen Projekts",
    aiEngineerTitle: "AI Engineer",
    aiEngineerIdleTitle: "Bericht erscheint nach der Generierung",
    aiEngineerIdleText:
      "Erstellen Sie zuerst ein Projekt. AI Engineer andert keine Dateien — nur Empfehlungen.",
    aiEngineerScoreLabel: "Gesamtbewertung",
    aiEngineerCheckedTitle: "Gepruft",
    aiEngineerFindingsTitle: "Hinweise",
    aiEngineerDisclaimer: "Alle Hinweise sind Empfehlungen. AI Engineer andert das Projekt nicht.",
    aiEngineerNoFindings: "Keine Hinweise",
    aiEngineerOneFinding: "1 Empfehlung",
    aiEngineerManyFindings: "{count} Empfehlungen",
    aiEngineerCriticalNone: "🟢 Keine kritischen Hinweise",
    aiEngineerModeRules: "Regeln",
    aiEngineerModeLlm: "Regeln + LLM",
    aiEngineerViewAction: "Warum?",
    aiEngineerHideAction: "Ausblenden",
    aiEngineerFixAction: "Wie lösen?",
    aiEngineerHideFixAction: "Lösung ausblenden",
    aiEngineerChatTitle: "Ingenieur im Chat",
    aiEngineerChatLive: "Online · kennt dieses Projekt",
    aiEngineerChatStandby: "Online · Normen und Regeln",
    aiEngineerChatGhostUser: "Wie viele F207 an A23?",
    aiEngineerChatGhostBot: "Fragen Sie auch ohne Projekt: Normen, Armaturen, PP23. Ist die Notiz fertig, gehen wir die Hinweise zum Plan durch.",
    aiEngineerChatHint: "Fragen zu VL-Normen oder zu diesem Projekt. Ein Projekt ist optional — Luna antwortet so oder so.",
    aiEngineerChatPlaceholder: "Frage zu Normen oder zum Projekt…",
    aiEngineerChatSend: "Fragen",
    aiEngineerChatWait: "Denke nach…",
    aiEngineerChatEmpty: "Stellen Sie eine Frage — z. B. worin sich PP23 von P23 unterscheidet.",
    aiEngineerChatYou: "Sie",
    aiEngineerChatBot: "AI Engineer",
    aiEngineerChatNeedProject: "Zuerst ein Projekt erzeugen.",
    aiEngineerChatError: "Antwort fehlgeschlagen.",
    aiEngineerGeometryAlert: "AI Engineer: Stuetzen/Erdungen nicht auf der 0,4-kV-Polylinie",
    aiEngineerCardAlert: "AI: Plan korrigieren",
    footer: "TU-Automatisierung — Werkzeug fur Projektdokumentation",
    dockStart: "Start",
    dockNote: "Notiz laden",
    dockPdf: "PDF laden",
    addParallelProject: "Paralleles Projekt",
    projectsListTitle: "Projektwarteschlange",
    projectsListHint: "Lokaler Server: Projekte laufen parallel mit eigenem Fortschritt und Download.",
    parallelFormReady: "Form freigemacht. TU und Plan fur das nachste Projekt laden.",
    projectRunning: "Wird bearbeitet…",
    projectReady: "Bereit zum Download",
    projectFailed: "Fehler",
    projectCardTitle: "Projekt {code}",
    projectStageReady: "Fertig",
    projectStageFailed: "Fehler",
    projectStageRunning: "Verarbeitung…",
    projectDownloadNote: "Laden",
    projectDownloadPdf: "PDF",
    projectType04: "0,4 kV",
    projectType10: "10 kV",
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
    themeLabel: "Tema",
    settingsOpen: "Impostazioni",
    settingsTitle: "Impostazioni",
    themeLight: "Tema chiaro",
    themeDark: "Tema scuro",
    statusIdleTitle: "Coda e progresso",
    statusIdleText: "Dopo l'avvio qui compaiono il progresso e l'elenco dei progetti.",
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
    stepTu: "TU analizzati",
    stepPlan: "Analisi piano",
    stepMap: "Mappa sostituzioni",
    stepDwg: "Generazione nota",
    stepDone: "Pronto",
    cardOneTitle: "Rileva il tipo di progetto",
    cardOneText: "Capisce da sola se è 0,4 kV o 10 kV dal TU e dal piano, poi sceglie il modello di nota adatto.",
    cardTwoTitle: "Legge il piano pronto",
    cardTwoText: "Calcola lunghezza linea, sostegni e messa a terra. Il disegno non cambia — solo i dati.",
    cardThreeTitle: "Prepara la nota",
    cardThreeText: "Compila una copia del modello con numero progetto, dati TU e calcoli, poi offre il file per il download.",
    tabProject: "Progetto",
    aiEngineerTab: "AI Engineer",
    aiEngineerEyebrow: "Verifica post-generazione",
    aiEngineerTitle: "AI Engineer",
    aiEngineerIdleTitle: "Il report appare dopo la generazione",
    aiEngineerIdleText:
      "Prima genera un progetto. AI Engineer non modifica i file — solo raccomandazioni.",
    aiEngineerScoreLabel: "Valutazione complessiva",
    aiEngineerCheckedTitle: "Controllato",
    aiEngineerFindingsTitle: "Osservazioni",
    aiEngineerDisclaimer: "Tutte le osservazioni sono raccomandazioni. AI Engineer non modifica il progetto.",
    aiEngineerNoFindings: "Nessuna osservazione",
    aiEngineerOneFinding: "1 raccomandazione",
    aiEngineerManyFindings: "{count} raccomandazioni",
    aiEngineerCriticalNone: "🟢 Nessun rilievo critico",
    aiEngineerModeRules: "Regole",
    aiEngineerModeLlm: "Regole + LLM",
    aiEngineerViewAction: "Perché?",
    aiEngineerHideAction: "Nascondi",
    aiEngineerFixAction: "Come risolvere?",
    aiEngineerHideFixAction: "Nascondi soluzione",
    aiEngineerChatTitle: "Ingegnere in chat",
    aiEngineerChatLive: "Online · conosce questo progetto",
    aiEngineerChatStandby: "Online · norme e regole",
    aiEngineerChatGhostUser: "Quanti F207 su A23?",
    aiEngineerChatGhostBot: "Puoi chiedere anche senza progetto: norme, armature, PP23. Quando la nota è pronta, analizziamo i rilievi del piano.",
    aiEngineerChatHint: "Chiedi sulle norme VL o su questo progetto. Il progetto è opzionale — Luna risponde comunque.",
    aiEngineerChatPlaceholder: "Domanda su norme o sul progetto…",
    aiEngineerChatSend: "Chiedi",
    aiEngineerChatWait: "Sto pensando…",
    aiEngineerChatEmpty: "Fai una domanda — ad esempio in cosa PP23 differisce da P23.",
    aiEngineerChatYou: "Tu",
    aiEngineerChatBot: "AI Engineer",
    aiEngineerChatNeedProject: "Prima genera un progetto.",
    aiEngineerChatError: "Impossibile ottenere una risposta.",
    aiEngineerGeometryAlert: "AI Engineer: sostegni/messa a terra fuori dalla polilinea 0,4 kV",
    aiEngineerCardAlert: "AI: correggi il piano",
    footer: "Automazione TU — strumento tecnico per documentazione di progetto",
    dockStart: "Avvia",
    dockNote: "Scarica nota",
    dockPdf: "Scarica PDF",
    addParallelProject: "Progetto parallelo",
    projectsListTitle: "Coda progetti",
    projectsListHint: "Server locale: i progetti avanzano in parallelo con progresso e download propri.",
    parallelFormReady: "Modulo svuotato. Carica TU e piano per il progetto successivo.",
    projectRunning: "In elaborazione…",
    projectReady: "Pronto al download",
    projectFailed: "Errore",
    projectCardTitle: "Progetto {code}",
    projectStageReady: "Pronto",
    projectStageFailed: "Errore",
    projectStageRunning: "Elaborazione…",
    projectDownloadNote: "Scarica",
    projectDownloadPdf: "PDF",
    projectType04: "0,4 kV",
    projectType10: "10 kV",
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
let displayedOverallProgress = 0;
let languageAnimationTimers = [];
let themeAnimationTimer = null;

const statusTimeline = [
  { step: "files_uploaded", stateKey: "stateFiles", labelKey: "stepFiles" },
  { step: "tu_extracted", stateKey: "stateTu", labelKey: "stepTu" },
  { step: "plan_analyzed", stateKey: "statePlan", labelKey: "stepPlan" },
  { step: "replacement_map_created", stateKey: "stateMap", labelKey: "stepMap" },
  { step: "dwg_filled", stateKey: "stateDwg", labelKey: "stepDwg" },
  { step: "completed", stateKey: "statePdf", labelKey: "stepDone" },
];

const STEP_WEIGHTS = {
  files_uploaded: 8,
  tu_extracted: 18,
  plan_analyzed: 34,
  replacement_map_created: 50,
  dwg_filled: 88,
  completed: 100,
};

// cursor-light и scroll-idle отключены: давали постоянный rAF и дрожь UI.

// pointer-glow на liquid-control отключён (rAF на каждом движении мыши).

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

settingsTrigger?.addEventListener("click", (event) => {
  event.stopPropagation();
  const willOpen = !settingsMenu?.classList.contains("is-open");
  setWireMenuOpen(false);
  setLanguageMenuOpen(false);
  setSettingsMenuOpen(willOpen);
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
  if (settingsMenu && !settingsMenu.contains(event.target)) {
    setSettingsMenuOpen(false);
    setLanguageMenuOpen(false);
  }
  if (!languagePicker.contains(event.target)) {
    setLanguageMenuOpen(false);
  }
  if (!wirePicker.contains(event.target)) {
    setWireMenuOpen(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setSettingsMenuOpen(false);
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
      steps: { files_uploaded: true },
      progress: 10,
      stageLabel: t("stepFiles"),
      message: "",
      aiEngineer: null,
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
  if (activeJobsCount <= 1) {
    resetStatus();
  }
  setLiveStatusVisible(true);
  if (runEntry.id === selectedRunId || activeJobsCount <= 1) {
    applySteps(runEntry.steps || { files_uploaded: true }, { active: true });
    setOverallProgress(Math.max(Number(runEntry.progress) || 0, 8), { allowDecrease: true });
    if (runEntry.stageLabel) {
      runState.textContent = runEntry.stageLabel;
    }
  }
  if (!progressTimer) {
    startProgressTimeline();
  }
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
    syncRunEntryProgress(runEntry, payload);
    if (noteReady) {
      runEntry.progress = 100;
      runEntry.stageLabel = t("projectStageReady");
      runEntry.aiEngineer = payload.ai_engineer || null;
    }
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
    await presentAiEngineerForRun(sessionId, runEntry, payload.ai_engineer || null, {
      switchTab: true,
      refresh: false,
      scroll: false,
    });
    const aiWarnText = formatAiEngineerNotice(runEntry.aiEngineer);
    showNotice(
      `${successMessage}${unresolvedNote}${formatWireSuccessNotice(payload)}${warningText}${aiWarnText}`,
      aiWarnText ? "error" : "success",
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
          syncRunEntryProgress(runEntry, recovered);
          runEntry.aiEngineer = recovered.ai_engineer || runEntry.aiEngineer || null;
          runEntry.progress = 100;
          runEntry.stageLabel = t("projectStageReady");
          upsertProjectRun(runEntry);
          selectProjectRun(sessionId);
          if (activeJobsCount <= 1) {
            stopProgressTimeline();
          }
          runState.textContent = t("ready");
          await presentAiEngineerForRun(sessionId, runEntry, runEntry.aiEngineer, {
            switchTab: true,
            refresh: false,
            scroll: false,
          });
          const aiWarnText = formatAiEngineerNotice(runEntry.aiEngineer);
          showNotice(
            `${recovered.project_type === "10kv" ? t("success10kv") : t("success")}${aiWarnText}`,
            aiWarnText ? "error" : "success",
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
    syncRunEntryProgress(runEntry, payload);
    upsertProjectRun(runEntry);

    if (runEntry.id === selectedRunId || activeJobsCount <= 1) {
      applySteps(runEntry.steps, { active: true });
      setOverallProgress(runEntry.progress);
      if (runEntry.stageLabel) {
        runState.textContent = runEntry.stageLabel;
      }
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
  if (aiEngineerChatLog && aiChatRunId !== runId) {
    aiEngineerChatLog.dataset.loaded = "0";
  }
  lastNoteDownloadUrl = entry.noteUrl || `/api/download/${runId}/note`;
  setDownloads(Boolean(entry.noteReady));
  if (entry.steps) {
    applySteps(entry.steps, {
      active: entry.status === "running",
      forceComplete: entry.status === "ready",
    });
    setOverallProgress(entry.progress || computeProgress(entry.steps, entry.status), {
      allowDecrease: true,
    });
  }
  if (entry.status === "running" && entry.stageLabel) {
    runState.textContent = entry.stageLabel;
  } else if (entry.status === "ready") {
    runState.textContent = t("ready");
  } else if (entry.status === "error") {
    runState.textContent = t("error");
  }
  if (entry.aiEngineer) {
    renderAiEngineerReport(entry.aiEngineer);
  } else if (entry.status === "ready") {
    void fetchAiEngineerReport(runId, entry);
  } else {
    renderAiEngineerReport(null);
  }
  renderProjectRuns();
}

function setWorkspaceTab(tabName) {
  const tab = tabName === "ai" ? "ai" : "project";
  document.body.classList.toggle("is-ai-tab", tab === "ai");
  if (workspaceRoot) {
    workspaceRoot.dataset.activeTab = tab;
  }
  workspaceTabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.workspaceTab === tab);
  });
  if (aiEngineerPanel) {
    aiEngineerPanel.hidden = tab !== "ai";
  }
  // Только показать уже готовый отчёт. Без refresh и без повторного setWorkspaceTab —
  // иначе возникает цикл перерисовок и страница «дёргается».
  if (tab === "ai" && selectedRunId) {
    const entry = projectRuns.find((item) => item.id === selectedRunId);
    if (entry?.aiEngineer) {
      renderAiEngineerReport(entry.aiEngineer);
    } else if (entry?.status === "ready") {
      void presentAiEngineerForRun(selectedRunId, entry, null, {
        switchTab: false,
        refresh: false,
        scroll: false,
      });
    } else {
      renderAiEngineerReport(null);
    }
  }
}

function renderAiEngineerReport(report) {
  const hasReport = Boolean(report && typeof report === "object");
  workspaceTabs.forEach((button) => {
    if (button.dataset.workspaceTab === "ai") {
      button.classList.toggle("has-report", hasReport);
    }
  });
  if (aiEngineerIdle) aiEngineerIdle.hidden = hasReport;
  if (aiEngineerReport) aiEngineerReport.hidden = !hasReport;
  aiChatHasProject = Boolean(hasReport && selectedRunId);
  if (!hasReport) {
    if (aiEngineerModeBadge) aiEngineerModeBadge.hidden = true;
    if (aiEngineerPlacement) {
      aiEngineerPlacement.hidden = true;
      aiEngineerPlacement.textContent = "";
    }
    syncAiChatState();
    void loadAiEngineerChat("");
    return;
  }

  const score = Number(report.score);
  if (aiEngineerScore) {
    aiEngineerScore.textContent = Number.isFinite(score) ? `${score.toFixed(1)}%` : "—";
  }
  if (aiEngineerSummary) {
    const status = String(report.status || "ok");
    aiEngineerSummary.className = `ai-engineer__summary is-${status}`;
    if (status === "ok") {
      aiEngineerSummary.textContent = t("aiEngineerCriticalNone");
    } else {
      aiEngineerSummary.textContent = report.summary || t("aiEngineerFindingsTitle");
    }
  }
  if (aiEngineerModeBadge) {
    const mode = String(report.mode || "rules");
    aiEngineerModeBadge.hidden = false;
    aiEngineerModeBadge.textContent =
      mode === "rules+llm" ? t("aiEngineerModeLlm") : t("aiEngineerModeRules");
  }
  if (aiEngineerChecked) {
    const items = Array.isArray(report.checked) ? report.checked : [];
    aiEngineerChecked.innerHTML = items
      .map((item) => {
        const attention = item.attention ? " is-attention" : "";
        const mark = item.attention ? "!" : item.ok ? "✔" : "○";
        return `<li class="${attention}"><span class="mark">${mark}</span><span>${escapeHtml(
          item.label || item.id || "",
        )}</span></li>`;
      })
      .join("");
  }
  if (aiEngineerPlacement) {
    const notes = Array.isArray(report.placement_notes)
      ? report.placement_notes.filter(Boolean)
      : [];
    aiEngineerPlacement.hidden = !notes.length;
    aiEngineerPlacement.textContent = notes.join(" ");
  }
  const findings = Array.isArray(report.findings) ? report.findings : [];
  if (aiEngineerFindingsCount) {
    if (!findings.length) {
      aiEngineerFindingsCount.textContent = t("aiEngineerNoFindings");
    } else if (report.summary) {
      aiEngineerFindingsCount.textContent = report.summary;
    } else if (findings.length === 1) {
      aiEngineerFindingsCount.textContent = t("aiEngineerOneFinding");
    } else {
      aiEngineerFindingsCount.textContent = t("aiEngineerManyFindings").replace(
        "{count}",
        String(findings.length),
      );
    }
  }
  if (aiEngineerFindings) {
    aiEngineerFindings.innerHTML = findings
      .map((item, index) => {
        const severity = String(item.severity || "recommendation");
        const severityClass =
          severity === "critical" ? "is-critical" : severity === "warning" ? "is-warning" : "";
        const why = String(item.why || item.detail || item.reason || "").trim();
        const how = String(item.how || "").trim();
        return `
          <article class="ai-engineer__finding ${severityClass}" data-finding-index="${index}">
            <p class="ai-engineer__finding-title">${escapeHtml(item.title || "")}</p>
            <p class="ai-engineer__finding-reason">${escapeHtml(item.reason || "")}</p>
            <p class="ai-engineer__finding-detail is-why">${escapeHtml(why)}</p>
            <p class="ai-engineer__finding-detail is-how">${escapeHtml(how || why)}</p>
            <div class="ai-engineer__finding-actions">
              <button type="button" class="ai-engineer__finding-action" data-finding-action="why">
                ${escapeHtml(item.action || t("aiEngineerViewAction"))}
              </button>
              <button type="button" class="ai-engineer__finding-action" data-finding-action="how">
                ${escapeHtml(item.fix_action || t("aiEngineerFixAction"))}
              </button>
            </div>
          </article>
        `;
      })
      .join("");
  }
  if (aiEngineerDisclaimer && report.disclaimer) {
    aiEngineerDisclaimer.textContent = report.disclaimer;
  }
  syncAiChatState();
  if (hasReport && selectedRunId) {
    void loadAiEngineerChat(selectedRunId);
  } else {
    void loadAiEngineerChat("");
  }
}

function syncAiChatState() {
  if (aiEngineerChat) {
    aiEngineerChat.classList.remove("is-locked");
    aiEngineerChat.classList.toggle("has-project", aiChatHasProject);
  }
  if (aiEngineerChatInput) aiEngineerChatInput.disabled = false;
  if (aiEngineerChatSend) aiEngineerChatSend.disabled = aiChatBusy;
  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.disabled = aiChatBusy;
  });
}

function renderAiEngineerChat(messages) {
  if (!aiEngineerChatLog) return;
  const items = Array.isArray(messages) ? messages : [];
  if (!items.length) {
    const you = escapeHtml(t("aiEngineerChatYou").slice(0, 1));
    aiEngineerChatLog.innerHTML = `
      <div class="ai-chat__preview" aria-hidden="true">
        <article class="ai-chat__bubble is-user is-ghost">
          <span class="ai-chat__avatar ai-chat__avatar--mini is-user">${you}</span>
          <div><span>${escapeHtml(t("aiEngineerChatYou"))}</span><p>${escapeHtml(t("aiEngineerChatGhostUser"))}</p></div>
        </article>
        <article class="ai-chat__bubble is-bot is-ghost">
          <span class="ai-chat__avatar ai-chat__avatar--mini"><img src="/static/icons/luna.jpg" alt=""></span>
          <div><span>${escapeHtml(t("aiEngineerChatBot"))}</span><p>${escapeHtml(t("aiEngineerChatGhostBot"))}</p></div>
        </article>
      </div>
      <div class="ai-chat__empty">
        <p>${escapeHtml(t("aiEngineerChatEmpty"))}</p>
      </div>`;
    return;
  }
  aiEngineerChatLog.innerHTML = items
    .map((item) => {
      const role = item.role === "user" ? "user" : "bot";
      const label = role === "user" ? t("aiEngineerChatYou") : t("aiEngineerChatBot");
      const avatar =
        role === "bot"
          ? `<span class="ai-chat__avatar ai-chat__avatar--mini"><img src="/static/icons/luna.jpg" alt=""></span>`
          : `<span class="ai-chat__avatar ai-chat__avatar--mini is-user">${escapeHtml(
              t("aiEngineerChatYou").slice(0, 1),
            )}</span>`;
      return `<article class="ai-chat__bubble is-${role}">${avatar}<div><span>${escapeHtml(
        label,
      )}</span><p>${escapeHtml(item.content || "")}</p></div></article>`;
    })
    .join("");
  aiEngineerChatLog.scrollTop = aiEngineerChatLog.scrollHeight;
}

function setAiChatTyping(isTyping) {
  if (aiEngineerChat) aiEngineerChat.classList.toggle("is-typing", Boolean(isTyping));
  if (aiEngineerChatTyping) aiEngineerChatTyping.hidden = !isTyping;
}

async function loadAiEngineerChat(runId) {
  if (!aiEngineerChatLog) return;
  const scope = runId || "__general__";
  if (aiChatRunId === scope && aiEngineerChatLog.dataset.loaded === "1") return;
  aiChatRunId = scope;
  aiEngineerChatLog.dataset.loaded = "0";
  const url = runId
    ? `/api/ai-engineer/${encodeURIComponent(runId)}/chat`
    : "/api/ai-engineer/chat";
  try {
    const response = await fetch(url);
    if (!response.ok) {
      renderAiEngineerChat([]);
      if (aiEngineerChatStatus) aiEngineerChatStatus.textContent = "";
      return;
    }
    const payload = await response.json();
    renderAiEngineerChat(payload.messages || []);
    aiEngineerChatLog.dataset.loaded = "1";
    if (aiEngineerChatStatus && payload.configured === false) {
      aiEngineerChatStatus.textContent = "";
    }
  } catch {
    renderAiEngineerChat([]);
  }
}

async function sendAiEngineerChat(message) {
  const text = String(message || "").trim();
  if (!text || aiChatBusy) return;
  const useProject = Boolean(aiChatHasProject && selectedRunId);
  const url = useProject
    ? `/api/ai-engineer/${encodeURIComponent(selectedRunId)}/chat`
    : "/api/ai-engineer/chat";
  aiChatBusy = true;
  if (aiEngineerChatSend) aiEngineerChatSend.disabled = true;
  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.disabled = true;
  });
  setAiChatTyping(true);
  if (aiEngineerChatStatus) aiEngineerChatStatus.textContent = t("aiEngineerChatWait");
  const current = [];
  if (aiEngineerChatLog) {
    const existing = [...aiEngineerChatLog.querySelectorAll(".ai-chat__bubble:not(.is-ghost)")].map((node) => ({
      role: node.classList.contains("is-user") ? "user" : "assistant",
      content: node.querySelector("p")?.textContent || "",
    }));
    current.push(...existing.filter((item) => item.content));
  }
  current.push({ role: "user", content: text });
  renderAiEngineerChat(current);
  try {
    let response;
    let lastError;
    for (let attempt = 0; attempt < 4; attempt += 1) {
      try {
        response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        lastError = null;
        break;
      } catch (error) {
        lastError = error;
        await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
      }
    }
    if (!response) throw lastError || new Error(t("aiEngineerChatError"));
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload.detail;
      const detailText = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg || item).join(" ")
          : t("aiEngineerChatError");
      throw new Error(detailText);
    }
    renderAiEngineerChat(payload.messages || current.concat([{ role: "assistant", content: payload.reply || "" }]));
    if (aiEngineerChatLog) aiEngineerChatLog.dataset.loaded = "1";
    aiChatRunId = useProject ? selectedRunId : "__general__";
    if (aiEngineerChatStatus) aiEngineerChatStatus.textContent = "";
    if (aiEngineerChatInput) aiEngineerChatInput.value = "";
  } catch (error) {
    if (aiEngineerChatStatus) {
      const raw = String(error && error.message ? error.message : "");
      const network = /load failed|failed to fetch|networkerror|abort|timeout|отмен/i.test(raw);
      aiEngineerChatStatus.textContent = network || !raw ? t("aiEngineerChatError") : raw;
    }
  } finally {
    aiChatBusy = false;
    setAiChatTyping(false);
    syncAiChatState();
  }
}

function formatAiEngineerNotice(report) {
  if (!report || typeof report !== "object") return "";
  const findings = Array.isArray(report.findings) ? report.findings : [];
  const geometry = findings.filter((item) => {
    const id = String(item?.id || "");
    return id.startsWith("support_off_route") || id.startsWith("grounding_off_route");
  });
  if (!geometry.length && report.status !== "warnings" && report.status !== "critical") {
    return "";
  }
  const summary = String(report.summary || "").trim();
  if (geometry.length) {
    const titles = geometry
      .slice(0, 4)
      .map((item) => String(item.title || "").trim())
      .filter(Boolean);
    const head = summary || t("aiEngineerGeometryAlert");
    return ` ${head}${titles.length ? ` (${titles.join("; ")})` : ""}`;
  }
  return summary ? ` ${summary}` : "";
}

async function presentAiEngineerForRun(
  runId,
  entry,
  fallbackReport = null,
  options = {},
) {
  if (!runId) return null;
  const switchTab = options.switchTab === true;
  const refresh = options.refresh === true;
  const scroll = options.scroll === true;
  let report = fallbackReport;

  if (report && Array.isArray(report.findings) && !refresh) {
    if (entry) entry.aiEngineer = report;
    renderAiEngineerReport(report);
    if (switchTab) {
      document.body.classList.add("is-ai-tab");
      if (workspaceRoot) workspaceRoot.dataset.activeTab = "ai";
      workspaceTabs.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.workspaceTab === "ai");
      });
      if (aiEngineerPanel) aiEngineerPanel.hidden = false;
    }
    return report;
  }

  const fetchSeq = ++aiReportFetchSeq;
  try {
    const qs = refresh ? "?refresh=1" : "";
    const response = await fetch(`/api/ai-engineer/${encodeURIComponent(runId)}${qs}`);
    if (response.ok) {
      report = await response.json();
    }
  } catch {
    // оставляем fallback
  }
  if (fetchSeq !== aiReportFetchSeq) {
    return entry?.aiEngineer || report || null;
  }
  if (!report) return null;
  if (entry) {
    entry.aiEngineer = report;
    renderProjectRuns();
  }
  renderAiEngineerReport(report);
  if (switchTab) {
    document.body.classList.add("is-ai-tab");
    if (workspaceRoot) workspaceRoot.dataset.activeTab = "ai";
    workspaceTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.workspaceTab === "ai");
    });
    if (aiEngineerPanel) aiEngineerPanel.hidden = false;
  }
  if (scroll && aiEngineerFindings) {
    aiEngineerFindings.scrollIntoView({ behavior: "auto", block: "nearest" });
  }
  return report;
}

async function fetchAiEngineerReport(runId, entry) {
  if (!runId) return;
  if (entry?.aiEngineer && Array.isArray(entry.aiEngineer.findings)) {
    renderAiEngineerReport(entry.aiEngineer);
    return;
  }
  try {
    await presentAiEngineerForRun(runId, entry, entry?.aiEngineer || null, {
      switchTab: false,
      refresh: false,
      scroll: false,
    });
  } catch {
    // отчёт необязателен для скачивания записки
  }
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
  updateSidePanelVisibility();
  if (!projectRuns.length) {
    projectsList.innerHTML = "";
    return;
  }

  projectsList.innerHTML = projectRuns
    .map((entry) => {
      const typeLabel =
        entry.projectType === "10kv" ? t("projectType10") : entry.projectType === "0.4kv" ? t("projectType04") : "";
      const progress = Math.max(0, Math.min(100, Number(entry.progress) || 0));
      const stage = getProjectStageView(entry);
      const title = t("projectCardTitle").replace("{code}", shortProjectCode(entry.projectNumber));
      const errorHtml =
        entry.status === "error" && entry.error
          ? `<div class="project-run__meta">${escapeHtml(entry.error)}</div>`
          : "";
      const aiSummary = String(entry.aiEngineer?.summary || "").trim();
      const aiHasWarn =
        entry.aiEngineer &&
        (entry.aiEngineer.status === "warnings" || entry.aiEngineer.status === "critical");
      const aiHtml = aiHasWarn
        ? `<div class="project-run__ai-alert">${escapeHtml(
            aiSummary || t("aiEngineerCardAlert"),
          )}</div>`
        : "";
      return `
        <article class="project-run ${entry.id === selectedRunId ? "is-selected" : ""} ${
          entry.status === "running" ? "is-running" : ""
        } ${entry.status === "ready" ? "is-ready" : ""} ${
          entry.status === "error" ? "is-error" : ""
        } ${aiHasWarn ? "has-ai-warn" : ""}" data-run-id="${entry.id}">
          <div class="project-run__header">
            <div class="project-run__title">${escapeHtml(title)}</div>
            ${typeLabel ? `<span class="project-run__badge">${escapeHtml(typeLabel)}</span>` : ""}
          </div>
          <div class="project-run__stage">
            <span class="project-run__stage-mark">${stage.mark}</span>
            <span>${escapeHtml(stage.label)}</span>
          </div>
          ${aiHtml}
          <div class="project-run__progress" aria-hidden="true">
            <div class="project-run__progress-track">
              <div class="project-run__progress-bar" style="width:${progress}%"></div>
            </div>
            <span class="project-run__progress-value">${progress}%</span>
          </div>
          ${errorHtml}
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

function shortProjectCode(projectNumber) {
  const raw = String(projectNumber || "").trim();
  if (!raw) return "—";
  const parts = raw.split("/");
  return parts[parts.length - 1] || raw;
}

function getProjectStageView(entry) {
  if (entry.status === "ready") {
    return { mark: "✔", label: t("projectStageReady") };
  }
  if (entry.status === "error") {
    return { mark: "!", label: entry.error || t("projectStageFailed") };
  }
  const active = getActiveStepKey(entry.steps || {});
  const label = active
    ? formatActiveStepLabel(active)
    : entry.stageLabel || t("projectStageRunning");
  return { mark: "⏳", label };
}

function syncRunEntryProgress(entry, payload = {}) {
  const steps = { ...(entry.steps || {}) };
  Object.entries(payload.steps || {}).forEach(([key, value]) => {
    if (value) {
      steps[key] = true;
    }
  });
  if (payload.status === "completed" || payload.status === "completed_with_warnings") {
    statusTimeline.forEach(({ step }) => {
      steps[step] = true;
    });
  }
  entry.steps = steps;
  entry.message = payload.message || entry.message || "";
  const incoming =
    payload.progress != null && payload.progress !== ""
      ? Number(payload.progress)
      : computeProgress(steps, entry.status === "ready" ? "ready" : payload.status);
  const floor = Number.isFinite(incoming) ? incoming : 0;
  entry.progress = Math.max(Number(entry.progress) || 0, floor);
  const active = getActiveStepKey(steps);
  entry.stageLabel = active ? formatActiveStepLabel(active) : entry.message || t("projectStageRunning");
  if (payload.status === "completed" || payload.status === "completed_with_warnings") {
    entry.stageLabel = t("projectStageReady");
    entry.progress = 100;
  }
  if (payload.ai_engineer) {
    entry.aiEngineer = payload.ai_engineer;
  }
  if (payload.status === "failed") {
    entry.stageLabel = payload.message || t("projectStageFailed");
  }
}

function computeProgress(steps = {}, status = "running") {
  if (status === "ready" || status === "completed" || status === "completed_with_warnings") {
    return 100;
  }
  let best = 0;
  statusTimeline.forEach(({ step }) => {
    if (steps?.[step]) {
      best = Math.max(best, STEP_WEIGHTS[step] || 0);
    }
  });
  if (status === "failed") {
    return Math.max(0, Math.min(99, best));
  }
  return Math.max(0, Math.min(99, best));
}

function progressCapForSteps(steps = {}) {
  const active = getActiveStepKey(steps);
  const target = STEP_WEIGHTS[active];
  if (target == null) return 99;
  return Math.max(0, Math.min(99, target - 1));
}

function getActiveStepKey(steps = {}) {
  for (const { step } of statusTimeline) {
    if (!steps?.[step]) return step;
  }
  return "completed";
}

function formatActiveStepLabel(step) {
  const item = statusTimeline.find((node) => node.step === step);
  const label = t(item?.labelKey || "projectStageRunning");
  if (step === "completed") return label;
  return label.endsWith("...") || label.endsWith("…") ? label : `${label}...`;
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

workspaceTabs.forEach((button) => {
  button.addEventListener("click", () => {
    setWorkspaceTab(button.dataset.workspaceTab || "project");
  });
});
if (openAiEngineerTab) {
  openAiEngineerTab.addEventListener("click", () => setWorkspaceTab("ai"));
}
if (aiEngineerFindings) {
  aiEngineerFindings.addEventListener("click", (event) => {
    const action = event.target?.closest?.("[data-finding-action]");
    if (!action) return;
    const card = action.closest(".ai-engineer__finding");
    if (!card) return;
    const kind = action.dataset.findingAction;
    if (kind === "why" || kind === "view") {
      const willOpen = !card.classList.contains("is-why-open");
      card.classList.toggle("is-why-open", willOpen);
      action.textContent = willOpen ? t("aiEngineerHideAction") : t("aiEngineerViewAction");
      return;
    }
    if (kind === "how") {
      const willOpen = !card.classList.contains("is-how-open");
      card.classList.toggle("is-how-open", willOpen);
      action.textContent = willOpen ? t("aiEngineerHideFixAction") : t("aiEngineerFixAction");
    }
  });
}
if (aiEngineerChatForm) {
  aiEngineerChatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void sendAiEngineerChat(aiEngineerChatInput?.value || "");
  });
}
document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    void sendAiEngineerChat(button.dataset.chatPrompt || button.textContent || "");
  });
});

applyTheme(false);
updateLanguagePickerUI();
updateWirePickerUI();
applyLanguage(false);
updateWireHint();
resetStatus();
updateSidePanelVisibility();
setWorkspaceTab("project");
renderAiEngineerReport(null);

function setLanguageMenuOpen(isOpen) {
  languagePicker.classList.toggle("is-open", isOpen);
  languageTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  languageMenu.hidden = !isOpen;
}

function setSettingsMenuOpen(isOpen) {
  if (!settingsMenu || !settingsTrigger || !settingsPanel) return;
  settingsMenu.classList.toggle("is-open", isOpen);
  settingsTrigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  settingsPanel.hidden = !isOpen;
  if (!isOpen) {
    setLanguageMenuOpen(false);
  }
}

function setLiveStatusVisible(visible) {
  if (liveStatusPanel) {
    liveStatusPanel.hidden = !visible;
  }
  if (visible) {
    updateBenefitCards({ activeStep: "files_uploaded" });
  }
  updateSidePanelVisibility();
}

function updateBenefitCards({ steps = null, activeStep = "", forceComplete = false, idle = false } = {}) {
  if (!benefitCards.length) return;

  if (idle) {
    benefitCards.forEach((card) => {
      card.classList.remove("is-active", "is-done", "is-pending");
    });
    return;
  }

  if (forceComplete) {
    benefitCards.forEach((card) => {
      card.classList.remove("is-active", "is-pending");
      card.classList.add("is-done");
    });
    return;
  }

  const step = activeStep || (steps ? getActiveStepKey(steps) : "files_uploaded");
  const stageOrder = ["detect", "analyze", "deliver"];
  const stepToStage = {
    files_uploaded: "detect",
    tu_extracted: "detect",
    plan_analyzed: "analyze",
    replacement_map_created: "deliver",
    dwg_filled: "deliver",
    completed: "deliver",
  };

  if (step === "completed") {
    benefitCards.forEach((card) => {
      card.classList.remove("is-active", "is-pending");
      card.classList.add("is-done");
    });
    return;
  }

  const activeStage = stepToStage[step] || "detect";
  const activeIdx = stageOrder.indexOf(activeStage);

  benefitCards.forEach((card) => {
    const idx = stageOrder.indexOf(card.dataset.stage);
    const isDone = idx >= 0 && idx < activeIdx;
    const isActive = idx === activeIdx;
    card.classList.toggle("is-done", isDone);
    card.classList.toggle("is-active", isActive);
    card.classList.toggle("is-pending", !isDone && !isActive);
  });
}

function updateSidePanelVisibility() {
  const hasRuns = projectRuns.length > 0;
  const liveVisible = Boolean(liveStatusPanel && !liveStatusPanel.hidden);
  if (projectsPanel) {
    projectsPanel.hidden = !hasRuns;
    projectsPanel.classList.toggle("is-after-live", liveVisible && hasRuns);
  }
  if (statusIdleHint) {
    statusIdleHint.hidden = liveVisible || hasRuns;
  }
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
    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
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
      updateStatusMarks();
      if (!progressTimer) {
        runState.textContent = t("idle");
      } else {
        const entry = projectRuns.find((item) => item.id === selectedRunId);
        runState.textContent = entry?.stageLabel || t("processingStarted");
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
      const entry = projectRuns.find((item) => item.id === selectedRunId);
      if (entry?.stageLabel) {
        return { node, text: entry.stageLabel };
      }
      key = "processingStarted";
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
    item.classList.remove("is-active", "is-pending");
  }
  updateStatusMarks();
}

function setActiveStep(step) {
  statusItems.forEach((item) => {
    const isActive = item.dataset.step === step && !item.classList.contains("is-done");
    item.classList.toggle("is-active", isActive);
    item.classList.toggle(
      "is-pending",
      !item.classList.contains("is-done") && !isActive,
    );
  });
  updateStatusMarks();
  updateBenefitCards({ activeStep: step });
}

function updateStatusMarks() {
  statusItems.forEach((item) => {
    const mark = item.querySelector(".status-mark");
    const label = item.querySelector(".status-label");
    if (!mark) return;
    if (item.classList.contains("is-done")) {
      mark.textContent = "✔";
      if (label && label.dataset.i18n) {
        label.textContent = t(label.dataset.i18n);
      }
      return;
    }
    if (item.classList.contains("is-active")) {
      mark.textContent = "⏳";
      if (label && label.dataset.i18n) {
        const base = t(label.dataset.i18n);
        label.textContent =
          item.dataset.step === "completed" || base.endsWith("...") || base.endsWith("…")
            ? base
            : `${base}...`;
      }
      return;
    }
    mark.textContent = "○";
    if (label && label.dataset.i18n) {
      label.textContent = t(label.dataset.i18n);
    }
  });
}

function applySteps(steps = {}, options = {}) {
  const { active = true, forceComplete = false } = options;
  statusTimeline.forEach(({ step }) => {
    setStep(step, forceComplete || steps?.[step] === true);
  });
  if (forceComplete) {
    statusItems.forEach((item) => item.classList.remove("is-active", "is-pending"));
    updateStatusMarks();
    setOverallProgress(100);
    updateBenefitCards({ forceComplete: true });
    return;
  }
  if (active) {
    const current = getActiveStepKey(steps);
    setActiveStep(current);
    updateBenefitCards({ steps, activeStep: current });
  } else {
    statusItems.forEach((item) => item.classList.remove("is-active"));
    updateStatusMarks();
    updateBenefitCards({ steps, activeStep: getActiveStepKey(steps) });
  }
}

function setOverallProgress(percent, options = {}) {
  const allowDecrease = Boolean(options.allowDecrease);
  let value = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
  if (!allowDecrease) {
    value = Math.max(displayedOverallProgress, value);
  }
  displayedOverallProgress = value;
  if (statusProgressBar) {
    statusProgressBar.style.width = `${value}%`;
  }
  if (statusProgressValue) {
    statusProgressValue.textContent = `${value}%`;
  }
}

function startProgressTimeline() {
  stopProgressTimeline();
  progressTimer = window.setInterval(() => {
    crawlRunningProgress();
  }, 1800);
}

function crawlRunningProgress() {
  let changed = false;
  projectRuns.forEach((entry) => {
    if (entry.status !== "running") return;
    const cap = progressCapForSteps(entry.steps || {});
    const current = Math.max(0, Number(entry.progress) || 0);
    if (current >= cap) return;
    entry.progress = current + 1;
    changed = true;
    if (entry.id === selectedRunId || activeJobsCount <= 1) {
      setOverallProgress(entry.progress);
    }
  });
  if (changed) {
    renderProjectRuns();
  }
}

function stopProgressTimeline() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
  statusItems.forEach((item) => item.classList.remove("is-active"));
  updateStatusMarks();
}

function resetStatus() {
  stopProgressTimeline();
  displayedOverallProgress = 0;
  statusItems.forEach((item) => item.classList.remove("is-done", "is-active", "is-pending"));
  updateStatusMarks();
  setOverallProgress(0, { allowDecrease: true });
  runState.textContent = t("idle");
  updateBenefitCards({ idle: true });
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
