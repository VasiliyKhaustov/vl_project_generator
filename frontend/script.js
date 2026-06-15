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
    heroCopy: "Загрузите ТУ и готовый DWG/DXF-план, укажите номер проекта — система подготовит пояснительную записку и полный PDF-комплект.",
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
    cardThreeText: "После обработки можно скачать записку и итоговый PDF, если экспорт доступен.",
    footer: "Автоматизация ТУ — инженерный инструмент для подготовки проектной документации",
    dockStart: "Старт",
    dockNote: "Скачать записку",
    dockPdf: "Скачать PDF",
    stateFiles: "Передача файлов",
    stateTu: "Чтение ТУ",
    statePlan: "Анализ плана",
    stateMap: "Создание карты замен",
    stateDwg: "Заполнение DWG",
    statePdf: "Сборка PDF",
    ready: "Готово",
    check: "Проверьте",
    error: "Ошибка",
    validationProjectEmpty: "Введите номер проекта.",
    validationProjectFormat: "Номер проекта должен соответствовать формату ПСД/48/2026/XXX или ПСД/48/2026/XXX-СУФФИКС.",
    validationTu: "Выберите файл ТУ DOCX/PDF.",
    validationPlan: "Выберите файл плана DWG/DXF.",
    processError: "Не удалось обработать проект.",
    processingStarted: "Обработка запущена. Обычно это занимает 3–8 минут: чтение ТУ, расчёт километража, заполнение DWG и сборка PDF.",
    unresolved: "Часть полей не заменена:",
    checkLog: "Проверьте log.txt.",
    success: "Пояснительная записка сформирована. Поля заменены.",
    pdfUnavailable: "PDF пока недоступен.",
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
    pdfUnavailable: "PDF is not available yet.",
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

window.addEventListener("pointermove", (event) => {
  if (cursorLight) {
    cursorLight.style.left = `${event.clientX}px`;
    cursorLight.style.top = `${event.clientY}px`;
  }
});

liquidTargets.forEach((target) => {
  target.addEventListener("pointermove", (event) => {
    const rect = target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    target.style.setProperty("--mx", `${x}px`);
    target.style.setProperty("--my", `${y}px`);
    target.style.setProperty("--pull-x", `${(x / rect.width - 0.5) * 4}px`);
    target.style.setProperty("--pull-y", `${(y / rect.height - 0.5) * 4}px`);
  });
  target.addEventListener("pointerleave", () => {
    target.style.setProperty("--pull-x", "0px");
    target.style.setProperty("--pull-y", "0px");
  });
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
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice();
  resetStatus();
  setDownloads(false);

  const validation = validateForm();
  if (validation) {
    showNotice(validation, "error");
    return;
  }

  const body = new FormData(form);
  syncWireFormFields();
  body.set("project_number", projectNumber.value.trim());
  body.set("wire_selection_mode", wireSelectionMode.value);
  if (wireManualValue.value) {
    body.set("wire_manual_value", wireManualValue.value);
  } else {
    body.delete("wire_manual_value");
  }

  startButton.disabled = true;
  startProgressTimeline();
  showNotice(t("processingStarted"), "success");

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

    stopProgressTimeline();
    applySteps(payload.steps);

    const unresolved = payload.cad?.unresolved_placeholders || [];
    const warningText = payload.warnings?.length ? ` ${payload.warnings.join(" ")}` : "";

    if (unresolved.length) {
      setDownloads(false);
      runState.textContent = t("check");
      showNotice(`${t("unresolved")} ${unresolved.join(", ")}. ${t("checkLog")}${warningText}`, "error");
      return;
    }

    setDownloads(true);
    runState.textContent = t("ready");
    showNotice(`${t("success")}${formatWireSuccessNotice(payload)}${warningText}`, "success");
  } catch (error) {
    stopProgressTimeline();
    runState.textContent = t("error");
    showNotice(error.message, "error");
  } finally {
    startButton.disabled = false;
  }
});

downloadNote.addEventListener("click", () => {
  window.location.href = "/api/download/note";
});

downloadPdf.addEventListener("click", async () => {
  const response = await fetch("/api/download/final-pdf");
  if (response.status === 202) {
    const payload = await response.json();
    showNotice(payload.message, "success");
    return;
  }

  if (!response.ok) {
    showNotice(t("pdfUnavailable"), "error");
    return;
  }

  window.location.href = "/api/download/final-pdf";
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
      updateWirePickerUI();
      updateWireHint();
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
  downloadNote.disabled = !enabled;
  downloadPdf.disabled = !enabled;
}

function showNotice(message, type) {
  notice.textContent = message;
  notice.className = `notice is-visible is-${type}`;
}

function clearNotice() {
  notice.textContent = "";
  notice.className = "notice";
}
