const state = {
  initialized: false,
  pollingTimer: null,
  lastSilTimestamp: null,
  selectedIteration: null,
  selectedHistoryFile: null,
  historyQuery: "",
  historyFilter: "all",
  latestLoopState: null,
  latestHistory: [],
  latestSilLog: [],
  currentGreeting: "",
  currentView: "main",
  chatAttachments: [],
  viewerAttachment: null,
  titleIntroReady: false,
  titleDataReady: false,
  titleScreenDismissed: false,
};

const els = {
  greeting: document.getElementById("greeting"),
  serviceMode: document.getElementById("serviceMode"),
  serviceModel: document.getElementById("serviceModel"),
  awayDays: document.getElementById("awayDays"),
  loopTotal: document.getElementById("loopTotal"),
  viewButtonMain: document.getElementById("viewButtonMain"),
  viewButtonWorkroom: document.getElementById("viewButtonWorkroom"),
  viewButtonArchive: document.getElementById("viewButtonArchive"),
  viewSummaryMain: document.getElementById("viewSummaryMain"),
  viewSummaryWorkroom: document.getElementById("viewSummaryWorkroom"),
  viewSummaryArchive: document.getElementById("viewSummaryArchive"),
  settingsBase: document.getElementById("settingsBase"),
  settingsSpoiler: document.getElementById("settingsSpoiler"),
  settingsStyle: document.getElementById("settingsStyle"),
  titleInput: document.getElementById("titleInput"),
  maxLoopsInput: document.getElementById("maxLoopsInput"),
  contextModeInput: document.getElementById("contextModeInput"),
  earlyStopInput: document.getElementById("earlyStopInput"),
  parallelInput: document.getElementById("parallelInput"),
  recentContextInput: document.getElementById("recentContextInput"),
  summaryInput: document.getElementById("summaryInput"),
  plotInput: document.getElementById("plotInput"),
  estimateSummary: document.getElementById("estimateSummary"),
  saveSettingsButton: document.getElementById("saveSettingsButton"),
  estimateButton: document.getElementById("estimateButton"),
  runButton: document.getElementById("runButton"),
  cancelButton: document.getElementById("cancelButton"),
  systemNotice: document.getElementById("systemNotice"),
  chatStatusBanner: document.getElementById("chatStatusBanner"),
  chatThread: document.getElementById("chatThread"),
  threadMeta: document.getElementById("threadMeta"),
  quickRunSummary: document.getElementById("quickRunSummary"),
  quickRunMeta: document.getElementById("quickRunMeta"),
  quickSelectionSummary: document.getElementById("quickSelectionSummary"),
  loopStatusText: document.getElementById("loopStatusText"),
  loopStageText: document.getElementById("loopStageText"),
  loopProgressMeta: document.getElementById("loopProgressMeta"),
  runMeta: document.getElementById("runMeta"),
  progressPercent: document.getElementById("progressPercent"),
  progressBar: document.getElementById("progressBar"),
  progressCaption: document.getElementById("progressCaption"),
  loopCards: document.getElementById("loopCards"),
  latestFinal: document.getElementById("latestFinal"),
  finalMeta: document.getElementById("finalMeta"),
  reflectionSummary: document.getElementById("reflectionSummary"),
  selectedIterationBadge: document.getElementById("selectedIterationBadge"),
  exportSelectedMarkdownButton: document.getElementById("exportSelectedMarkdownButton"),
  exportSelectedJsonButton: document.getElementById("exportSelectedJsonButton"),
  iterationRail: document.getElementById("iterationRail"),
  iterationFocus: document.getElementById("iterationFocus"),
  historySearchInput: document.getElementById("historySearchInput"),
  historyFilterInput: document.getElementById("historyFilterInput"),
  exportHistoryMarkdownButton: document.getElementById("exportHistoryMarkdownButton"),
  exportHistoryJsonButton: document.getElementById("exportHistoryJsonButton"),
  historyList: document.getElementById("historyList"),
  historyDetail: document.getElementById("historyDetail"),
  silLogList: document.getElementById("silLogList"),
  silhouette: document.getElementById("silhouette"),
  personaRune: document.getElementById("persona-rune"),
  personaCanon: document.getElementById("persona-canon"),
  personaEcho: document.getElementById("persona-echo"),
  personaSil: document.getElementById("persona-sil"),
  lineRune: document.getElementById("line-rune"),
  lineCanon: document.getElementById("line-canon"),
  lineEcho: document.getElementById("line-echo"),
  lineSil: document.getElementById("line-sil"),
  attachmentViewer: document.getElementById("attachmentViewer"),
  viewerBackdrop: document.getElementById("viewerBackdrop"),
  viewerPersona: document.getElementById("viewerPersona"),
  viewerTitle: document.getElementById("viewerTitle"),
  viewerMeta: document.getElementById("viewerMeta"),
  viewerContent: document.getElementById("viewerContent"),
  downloadViewerMarkdownButton: document.getElementById("downloadViewerMarkdownButton"),
  closeViewerButton: document.getElementById("closeViewerButton"),
  titleScreen: document.getElementById("titleScreen"),
  titleStartButton: document.getElementById("titleStartButton"),
  titleStatus: document.getElementById("titleStatus"),
};

document.addEventListener("DOMContentLoaded", async () => {
  initTitleScreen();
  wireEvents();
  await loadState();
});

function wireEvents() {
  els.titleStartButton.addEventListener("click", dismissTitleScreen);
  els.titleScreen.addEventListener("click", handleTitleScreenClick);
  window.addEventListener("keydown", handleTitleKeydown);
  els.viewButtonMain.addEventListener("click", () => setActiveView("main"));
  els.viewButtonWorkroom.addEventListener("click", () => setActiveView("workroom"));
  els.viewButtonArchive.addEventListener("click", () => setActiveView("archive"));
  els.saveSettingsButton.addEventListener("click", saveSettings);
  els.estimateButton.addEventListener("click", estimateCost);
  els.runButton.addEventListener("click", startRun);
  els.cancelButton.addEventListener("click", cancelRun);
  els.historySearchInput.addEventListener("input", handleHistorySearch);
  els.historyFilterInput.addEventListener("change", handleHistoryFilter);
  els.exportSelectedMarkdownButton.addEventListener("click", () => exportSelectedIteration("markdown"));
  els.exportSelectedJsonButton.addEventListener("click", () => exportSelectedIteration("json"));
  els.exportHistoryMarkdownButton.addEventListener("click", () => exportSelectedHistory("markdown"));
  els.exportHistoryJsonButton.addEventListener("click", () => exportSelectedHistory("json"));
  els.downloadViewerMarkdownButton.addEventListener("click", downloadViewerAttachment);
  els.closeViewerButton.addEventListener("click", closeAttachmentViewer);
  els.viewerBackdrop.addEventListener("click", closeAttachmentViewer);
}

function initTitleScreen() {
  updateTitleStatus("로컬 서고를 깨우는 중...");
  document.body.classList.add("title-active");

  window.requestAnimationFrame(() => {
    els.titleScreen.classList.add("ready");
  });

  window.setTimeout(() => {
    state.titleIntroReady = true;
    syncTitleScreenState();
  }, 1400);
}

function handleTitleScreenClick(event) {
  if (event.target.closest("button")) {
    return;
  }
  dismissTitleScreen();
}

function handleTitleKeydown(event) {
  if (!["Enter", " "].includes(event.key)) {
    return;
  }
  if (event.target instanceof HTMLElement) {
    const tagName = event.target.tagName;
    if (["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(tagName)) {
      return;
    }
  }
  dismissTitleScreen(event);
}

function syncTitleScreenState() {
  const ready = state.titleIntroReady && state.titleDataReady;
  els.titleStartButton.disabled = !ready;
  els.titleStartButton.textContent = ready ? "서고 열기" : "동기화 중";
}

function updateTitleStatus(message) {
  els.titleStatus.textContent = message;
}

function dismissTitleScreen(event = null) {
  if (state.titleScreenDismissed || !state.titleIntroReady || !state.titleDataReady) {
    return;
  }
  if (event) {
    event.preventDefault();
  }

  state.titleScreenDismissed = true;
  els.titleScreen.setAttribute("aria-hidden", "true");
  document.body.classList.remove("title-active");
  document.body.classList.add("title-dismissed");

  window.setTimeout(() => {
    els.titleScreen.classList.add("hidden");
  }, 760);

  window.setTimeout(() => {
    els.plotInput.focus();
  }, 280);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "요청 처리 중 오류가 발생했습니다.");
  }

  return response.json();
}

async function loadState() {
  try {
    const data = await api("/api/state");
    renderFullState(data);
    state.initialized = true;
    syncPolling(data.loop_state);
    state.titleDataReady = true;
    updateTitleStatus("기록 정렬 완료. 서고에 입장할 수 있습니다.");
    syncTitleScreenState();
  } catch (error) {
    showNotice(error.message, true);
    state.titleDataReady = true;
    updateTitleStatus("연결 확인이 늦습니다. 그래도 입장할 수 있습니다.");
    syncTitleScreenState();
  }
}

function renderFullState(data) {
  state.currentGreeting = data.greeting || "";
  renderGreeting(data.greeting, data.meta, data.service);
  fillSettings(data.settings);
  renderLoopState(data.loop_state, data.meta);
  renderHistory(data.history || []);
  renderSilLog(data.sil_log || []);
  renderViewSummaries();
}

function setActiveView(view) {
  state.currentView = view;

  [
    ["main", els.viewButtonMain],
    ["workroom", els.viewButtonWorkroom],
    ["archive", els.viewButtonArchive],
  ].forEach(([name, button]) => {
    button.classList.toggle("selected", name === view);
  });

  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === view);
  });
}

function renderGreeting(greeting, meta, service) {
  els.greeting.textContent = greeting;
  els.serviceMode.textContent = service.mode;
  els.serviceModel.textContent = service.model;
  els.awayDays.textContent = `${meta.last_return_days || 0}일`;
  els.loopTotal.textContent = `${meta.total_completed_loops || 0}`;

  const lines = getPersonaLines(meta.affinity_stage || "distant");
  els.lineRune.textContent = lines.rune;
  els.lineCanon.textContent = lines.canon;
  els.lineEcho.textContent = lines.echo;
  els.lineSil.textContent = lines.sil;
}

function fillSettings(settings) {
  els.settingsBase.value = settings.base || "";
  els.settingsSpoiler.value = settings.spoiler || "";
  els.settingsStyle.value = settings.style || "";
}

function collectPayload() {
  return {
    title: els.titleInput.value.trim(),
    plot: els.plotInput.value.trim(),
    settings: {
      base: els.settingsBase.value,
      spoiler: els.settingsSpoiler.value,
      style: els.settingsStyle.value,
    },
    previous_context: {
      mode: els.contextModeInput.value,
      recent_full_text: els.recentContextInput.value,
      summary: els.summaryInput.value,
    },
    loop_config: {
      max_loops: Number(els.maxLoopsInput.value) || 3,
      early_stop_enabled: els.earlyStopInput.checked,
      parallel_feedback: els.parallelInput.checked,
    },
  };
}

async function saveSettings() {
  try {
    const payload = {
      settings: {
        base: els.settingsBase.value,
        spoiler: els.settingsSpoiler.value,
        style: els.settingsStyle.value,
      },
    };
    await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    showNotice("설정 문서를 저장했습니다.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function estimateCost() {
  const payload = collectPayload();
  if (!payload.plot) {
    showNotice("플롯을 먼저 입력하세요.", true);
    return;
  }

  setBusy(els.estimateButton, true);
  try {
    const result = await api("/api/cost-estimate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderEstimate(result);
    showNotice("예상 사용량을 갱신했습니다.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(els.estimateButton, false);
  }
}

function renderEstimate(result) {
  const total = result.total;
  const loops = result.loop_config.max_loops;
  const callRows = result.tokens_per_call
    .map(
      (item) =>
        `${labelForPersona(item.persona)} ${formatNumber(item.prompt_tokens)} + ${formatNumber(item.estimated_output_tokens)} · ${formatUsd(item.estimated_cost_usd, item.mode !== "api")}`
    )
    .join(" · ");

  els.estimateSummary.innerHTML = `
    <strong>${loops}회 루프 기준 약 ${formatNumber(total.total_tokens || total.prompt_tokens + total.estimated_output_tokens)} tokens</strong><br />
    예상 비용: ${formatUsd(total.estimated_cost_usd, Boolean(total.approximate))}<br />
    <span class="summary-tag">${callRows}</span>
  `;
}

async function startRun() {
  const payload = collectPayload();
  if (!payload.plot) {
    showNotice("플롯을 먼저 입력하세요.", true);
    return;
  }

  setBusy(els.runButton, true);
  try {
    await api("/api/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedIteration = null;
    setActiveView("main");
    showNotice("서고가 루프를 시작했습니다.");
    await refreshLivePanels();
    syncPolling({ status: "running" });
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(els.runButton, false);
    syncRunControls(state.latestLoopState || { status: "idle" });
  }
}

async function cancelRun() {
  if (state.latestLoopState?.status !== "running") {
    showNotice("지금은 취소할 실행 중인 루프가 없습니다.", true);
    syncRunControls(state.latestLoopState || { status: "idle" });
    return;
  }

  setBusy(els.cancelButton, true);
  try {
    const result = await api("/api/run/cancel", {
      method: "POST",
    });
    renderLoopState(result.loop_state);
    await refreshLivePanels();
    syncPolling(result.loop_state);
    showNotice("현재 루프를 중단했습니다.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(els.cancelButton, false);
    syncRunControls(state.latestLoopState || { status: "idle" });
  }
}

function renderLoopState(loopState, meta = null) {
  state.latestLoopState = loopState;
  const iterations = loopState.iterations || [];

  syncSelectedIteration(iterations, loopState);

  els.loopStatusText.textContent = loopState.message || "서고가 조용히 숨을 고르고 있습니다.";
  els.loopStageText.textContent = loopState.stage || "idle";
  syncRunControls(loopState);
  renderWorkflowOverview(loopState);
  renderLoopCards(loopState.cards || [], loopState.current_iteration || 0);
  renderLatestFinal(iterations);
  renderIterationRail(iterations);
  renderIterationFocus(iterations);
  renderThreadPanel(loopState);
  renderQuickLook(loopState);
  renderPersonaActivation(loopState.active_persona);

  if (meta) {
    const lines = getPersonaLines(meta.affinity_stage || "distant");
    els.lineRune.textContent = lines.rune;
    els.lineCanon.textContent = lines.canon;
    els.lineEcho.textContent = lines.echo;
  }
}

function renderThreadPanel(loopState) {
  els.chatStatusBanner.textContent =
    loopState.message || "저자가 플롯을 건네면 루네와 카논, 에코가 채팅처럼 응답합니다.";

  els.threadMeta.innerHTML = buildMetaPills([
    loopState.run_id ? `run ${loopState.run_id}` : "run 대기",
    `stage ${loopState.stage || "idle"}`,
    `loop ${loopState.current_iteration || 0}/${loopState.config?.max_loops || 0}`,
  ]);

  renderChatThread(loopState);
}

function renderQuickLook(loopState) {
  const selected = getSelectedIteration(loopState.iterations || []);
  const cards = loopState.cards || [];
  const done = cards.filter((card) => card.status === "done").length;
  const total = cards.length || Number(loopState.config?.max_loops || 0);

  if (!loopState.plot) {
    els.quickRunSummary.textContent = "플롯을 넣고 루프를 시작하면 대화가 여기서 움직입니다.";
    els.quickRunMeta.innerHTML = buildMetaPills(["idle", "대화 준비"]);
  } else {
    els.quickRunSummary.textContent = trimText(loopState.plot, 130);
    els.quickRunMeta.innerHTML = buildMetaPills([
      loopState.title || "untitled",
      `완료 ${done}/${total || 0}`,
      loopState.stage || "idle",
    ]);
  }

  els.quickSelectionSummary.textContent = selected
    ? `선택 루프 ${selected.loop_index}: ${selected.final_summary || selected.draft_summary || "대기 중"}`
    : "선택된 루프가 아직 없습니다.";
}

function renderChatThread(loopState) {
  const messages = buildChatMessages(loopState);
  state.chatAttachments = [];

  if (!messages.length) {
    els.chatThread.innerHTML = `<div class="empty-state">아직 열린 대화가 없습니다. 플롯을 넣어 첫 메시지를 시작하세요.</div>`;
    return;
  }

  els.chatThread.innerHTML = messages.map((message) => renderChatMessage(message)).join("");
  bindAttachmentButtons();
}

function buildChatMessages(loopState) {
  const messages = [];
  const iterations = loopState.iterations || [];

  if (state.currentGreeting) {
    messages.push({
      role: "system",
      persona: "system",
      personaLabel: "서고",
      stageLabel: "입구",
      text: state.currentGreeting,
      metaItems: buildSystemMessageMeta(loopState),
    });
  }

  if (loopState.plot) {
    messages.push({
      role: "author",
      persona: "author",
      personaLabel: loopState.title || "저자",
      stageLabel: "플롯 전달",
      text: loopState.plot,
      metaItems: buildAuthorMessageMeta(loopState),
    });
  }

  iterations.forEach((iteration) => {
    if (iteration.draft) {
      messages.push(
        buildStageMessage({
          persona: "rune",
          personaLabel: "루네",
          stageLabel: `Loop ${iteration.loop_index} · 초안`,
          text: iteration.draft_summary
            ? `초안을 md로 보낼게요. ${iteration.draft_summary}`
            : "초안을 md로 보낼게요.",
          attachment: buildStageAttachment(iteration, "draft"),
          metaItems: buildIterationMessageMeta(iteration, "draft"),
        })
      );
    }

    if (iteration.feedback) {
      messages.push(
        buildStageMessage({
          persona: "canon",
          personaLabel: "카논",
          stageLabel: `Loop ${iteration.loop_index} · 피드백`,
          text: iteration.feedback_summary || "설정과 흐름을 점검한 내용을 정리해 보냅니다.",
          attachment: buildStageAttachment(iteration, "feedback"),
          metaItems: buildIterationMessageMeta(iteration, "feedback"),
        })
      );
    }

    if (iteration.comment) {
      messages.push(
        buildStageMessage({
          persona: "echo",
          personaLabel: "에코",
          stageLabel: `Loop ${iteration.loop_index} · 댓글`,
          text: iteration.comment_summary || "읽는 쪽에서 느껴진 감각을 코멘트로 남깁니다.",
          attachment: buildStageAttachment(iteration, "comment"),
          metaItems: buildIterationMessageMeta(iteration, "comment"),
        })
      );
    }

    if (iteration.final) {
      messages.push(
        buildStageMessage({
          persona: "rune",
          personaLabel: "루네",
          stageLabel: `Loop ${iteration.loop_index} · 최종본`,
          text: buildFinalChatLine(iteration),
          attachment: buildStageAttachment(iteration, "final"),
          metaItems: buildIterationMessageMeta(iteration, "final"),
        })
      );
    }
  });

  if (loopState.status === "error" && loopState.error?.display) {
    messages.push({
      role: "sil",
      persona: "sil",
      personaLabel: "실",
      stageLabel: "오류 감지",
      text: loopState.error.display,
      metaItems: buildSilMessageMeta(loopState),
    });
  }

  return messages;
}

function buildStageMessage(payload) {
  return {
    role: "persona",
    ...payload,
  };
}

function buildFinalChatLine(iteration) {
  const lead = iteration.final_summary
    ? `반영한 최종본을 다시 올려둘게요. ${iteration.final_summary}`
    : "반영한 최종본을 다시 올려둘게요.";
  if (iteration.quality?.should_stop) {
    return `${lead} 이번 루프에서 묶어도 될 것 같아요.`;
  }
  return lead;
}

function buildSystemMessageMeta(loopState) {
  const items = [];
  if (loopState.status) {
    items.push(`status ${loopState.status}`);
  }
  if (loopState.config?.max_loops) {
    items.push(`max ${loopState.config.max_loops} loops`);
  }
  return items;
}

function buildAuthorMessageMeta(loopState) {
  const items = [];
  if (loopState.config?.max_loops) {
    items.push(`max ${loopState.config.max_loops} loops`);
  }
  items.push(loopState.config?.parallel_feedback ? "parallel feedback" : "serial feedback");
  items.push(loopState.config?.early_stop_enabled ? "early stop on" : "full run");
  return items.filter(Boolean);
}

function buildIterationMessageMeta(iteration, stage) {
  const items = [`loop ${iteration.loop_index}`, stage];
  if (iteration.status) {
    items.push(`status ${iteration.status}`);
  }

  if (stage === "final" && iteration.quality) {
    items.push(formatScore(iteration.quality));
    items.push(iteration.quality.should_stop ? "stop ready" : "continue");
  } else if (iteration.history_file) {
    items.push("saved");
  }

  return items.filter(Boolean).slice(0, 4);
}

function buildSilMessageMeta(loopState) {
  const items = [];
  if (loopState.status) {
    items.push(`status ${loopState.status}`);
  }
  if (loopState.error?.error_code) {
    items.push(loopState.error.error_code);
  }
  return items;
}

function renderChatMessage(message) {
  const roleClass =
    message.role === "author" ? "author" : message.role === "sil" ? "sil" : message.role;
  const metaMarkup =
    message.metaItems && message.metaItems.length
      ? `<div class="message-meta-row">${buildMetaPills(message.metaItems)}</div>`
      : "";

  let attachmentMarkup = "";
  if (message.attachment) {
    const index = state.chatAttachments.push(message.attachment) - 1;
    attachmentMarkup = `
      <button type="button" class="attachment-card" data-attachment-index="${index}">
        <div class="attachment-topline">
          <span class="attachment-title">${escapeHtml(message.attachment.displayTitle)}</span>
          <span class="file-badge">.md</span>
        </div>
        <div class="attachment-summary">${escapeHtml(message.attachment.summary)}</div>
      </button>
    `;
  }

  return `
    <div class="message-row ${roleClass}">
      <article class="message-bubble ${escapeHtml(message.persona)}">
        <div class="message-head">
          <span class="message-persona">${escapeHtml(message.personaLabel)}</span>
          <span class="message-stage">${escapeHtml(message.stageLabel || "")}</span>
        </div>
        ${metaMarkup}
        <div class="message-text">${escapeHtml(message.text || "")}</div>
        ${attachmentMarkup}
      </article>
    </div>
  `;
}

function buildStageAttachment(iteration, stage) {
  const stageMap = {
    draft: {
      label: "초안",
      field: "draft",
      summary: iteration.draft_summary || "초안 전문",
      personaLabel: "루네",
      filename: `loop-${String(iteration.loop_index).padStart(2, "0")}-draft.md`,
    },
    feedback: {
      label: "카논 피드백",
      field: "feedback",
      summary: iteration.feedback_summary || "설정/구조 피드백",
      personaLabel: "카논",
      filename: `loop-${String(iteration.loop_index).padStart(2, "0")}-canon-feedback.md`,
    },
    comment: {
      label: "에코 댓글",
      field: "comment",
      summary: iteration.comment_summary || "독자 반응 코멘트",
      personaLabel: "에코",
      filename: `loop-${String(iteration.loop_index).padStart(2, "0")}-echo-comment.md`,
    },
    final: {
      label: "최종본",
      field: "final",
      summary: iteration.final_summary || "최종본 전문",
      personaLabel: "루네",
      filename: `loop-${String(iteration.loop_index).padStart(2, "0")}-final.md`,
    },
  };

  const meta = stageMap[stage];
  const content = iteration[meta.field] || "";
  return {
    filename: meta.filename,
    displayTitle: `${meta.label} · Loop ${iteration.loop_index}`,
    personaLabel: meta.personaLabel,
    metaLine: `Loop ${iteration.loop_index} · ${meta.label}`,
    summary: meta.summary,
    content: buildAttachmentMarkdown(iteration, meta.label, content),
    iterationIndex: iteration.loop_index,
  };
}

function buildAttachmentMarkdown(iteration, label, content) {
  return [
    `# ${label}`,
    "",
    `- Loop: ${iteration.loop_index}`,
    `- Status: ${iteration.status || "-"}`,
    "",
    content || "",
    "",
  ].join("\n");
}

function bindAttachmentButtons() {
  document.querySelectorAll("[data-attachment-index]").forEach((button) => {
    button.addEventListener("click", () => {
      openAttachmentViewer(Number(button.dataset.attachmentIndex));
    });
  });
}

function openAttachmentViewer(index) {
  const attachment = state.chatAttachments[index];
  if (!attachment) {
    return;
  }

  state.viewerAttachment = attachment;
  state.selectedIteration = attachment.iterationIndex;
  if (state.latestLoopState) {
    renderLoopState(state.latestLoopState);
    renderViewSummaries();
  }

  els.viewerPersona.textContent = attachment.personaLabel;
  els.viewerTitle.textContent = attachment.displayTitle;
  els.viewerMeta.textContent = attachment.metaLine;
  els.viewerContent.textContent = attachment.content;
  els.attachmentViewer.classList.remove("hidden");
  els.attachmentViewer.setAttribute("aria-hidden", "false");
  document.body.classList.add("viewer-open");
}

function closeAttachmentViewer() {
  state.viewerAttachment = null;
  els.attachmentViewer.classList.add("hidden");
  els.attachmentViewer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("viewer-open");
}

function downloadViewerAttachment() {
  if (!state.viewerAttachment) {
    showNotice("내보낼 첨부 파일이 없습니다.", true);
    return;
  }

  downloadFile(
    state.viewerAttachment.filename,
    state.viewerAttachment.content,
    "text/markdown;charset=utf-8"
  );
  showNotice("첨부 파일을 Markdown으로 저장했습니다.");
}

function renderWorkflowOverview(loopState) {
  const cards = loopState.cards || [];
  const total = cards.length || Number(loopState.config?.max_loops || 0);
  const done = cards.filter((card) => card.status === "done").length;
  const skipped = cards.filter((card) => card.status === "skipped").length;
  const cancelled = cards.filter((card) => card.status === "cancelled").length;
  const resolved = done + skipped + cancelled;
  const remaining = Math.max(0, total - resolved);
  const percent = total ? Math.round((resolved / total) * 100) : 0;
  const currentIteration = loopState.current_iteration || 0;
  const usageSummary = loopState.usage_summary;

  els.loopProgressMeta.textContent =
    total > 0
      ? `총 ${total}회 중 ${done}회 완료, ${skipped}회 봉인, ${cancelled}회 중단, ${remaining}회 남음. 현재 회차는 ${currentIteration || "-"}입니다.`
      : "루프를 시작하면 현재 회차와 완료 상태가 정리됩니다.";

  els.progressPercent.textContent = `${percent}%`;
  els.progressBar.style.width = `${percent}%`;
  els.progressCaption.textContent = describeLoopProgress(
    loopState.status,
    done,
    skipped,
    cancelled,
    total
  );

  els.runMeta.innerHTML = buildMetaPills([
    loopState.run_id ? `run ${loopState.run_id}` : "run 대기",
    `회차 ${currentIteration || "-"}`,
    loopState.config?.early_stop_enabled ? "조기 종료 사용" : "끝까지 진행",
    loopState.config?.parallel_feedback ? "병렬 리뷰" : "순차 리뷰",
    formatUsageSummary(usageSummary),
  ]);
}

function describeLoopProgress(status, done, skipped, cancelled, total) {
  if (!total) {
    return "카드가 뒤집힐수록 진행률이 갱신됩니다.";
  }
  if (status === "running") {
    return `지금까지 ${done}개 루프가 보존됐고 ${skipped}개 루프가 봉인됐습니다.`;
  }
  if (status === "completed") {
    return "현재 루프가 끝났습니다. 작업실에서 세부 판단과 최종본을 확인하세요.";
  }
  if (status === "cancelled") {
    return `루프를 중단했습니다. ${cancelled}개 루프는 멈춘 지점에서 정리됐고, 남은 카드만 봉인됐습니다.`;
  }
  if (status === "error") {
    return "중간 기록은 남아 있습니다. Sil 로그와 선택 루프를 함께 확인하세요.";
  }
  return "루프를 시작하면 카드가 순서대로 갱신됩니다.";
}

function renderLoopCards(cards, currentIteration) {
  if (!cards.length) {
    els.loopCards.innerHTML = `<div class="empty-state">루프를 시작하면 카드가 뒤집힙니다.</div>`;
    return;
  }

  els.loopCards.innerHTML = cards
    .map((card) => {
      const status = card.status || (card.loop_index === currentIteration ? "active" : "pending");
      return `
        <article class="tarot-card ${status}">
          <span class="loop-number">${String(card.loop_index).padStart(2, "0")}</span>
          <span class="loop-caption">${cardLabel(status)}</span>
        </article>
      `;
    })
    .join("");
}

function renderLatestFinal(iterations) {
  const selected = getSelectedIteration(iterations);
  const source = selected?.final ? selected : [...iterations].reverse().find((item) => item.final);
  renderReflectionSummary(selected || source || null);

  if (!source) {
    els.latestFinal.classList.add("empty");
    els.latestFinal.textContent = "최종본이 아직 없습니다.";
    els.finalMeta.innerHTML = buildMetaPills(["최종본 없음"]);
    els.selectedIterationBadge.textContent = "선택된 루프 없음";
    return;
  }

  els.latestFinal.classList.remove("empty");
  els.latestFinal.textContent = source.final;
  els.finalMeta.innerHTML = buildMetaPills([
    `Loop ${source.loop_index}`,
    source.history_file ? `history ${source.history_file}` : "임시 상태",
    formatQualityLabel(source.quality),
  ]);
  els.selectedIterationBadge.textContent = `Loop ${source.loop_index}`;
}

function renderIterationRail(iterations) {
  if (!iterations.length) {
    els.iterationRail.innerHTML = `<div class="empty-state">루프가 시작되면 작업실에서 세부 회차를 볼 수 있습니다.</div>`;
    return;
  }

  els.iterationRail.innerHTML = iterations
    .map((iteration) => {
      const selected = iteration.loop_index === state.selectedIteration;
      const quality = formatQualityLabel(iteration.quality);
      return `
        <button
          type="button"
          class="iteration-tab ${selected ? "selected" : ""}"
          data-iteration="${iteration.loop_index}"
        >
          <span class="message-persona">Loop ${iteration.loop_index}</span>
          <strong>${escapeHtml(iteration.final_summary || iteration.draft_summary || "대기 중")}</strong>
          <span class="iteration-tab-meta">${escapeHtml(iteration.status || "pending")} · ${escapeHtml(quality)}</span>
        </button>
      `;
    })
    .join("");

  bindIterationButtons();
}

function renderIterationFocus(iterations) {
  const iteration = getSelectedIteration(iterations);
  if (!iteration) {
    els.iterationFocus.innerHTML = `<div class="empty-state">선택할 루프가 아직 없습니다.</div>`;
    return;
  }

  const stageCards = [
    buildStageCard("초안", iteration.draft, iteration.draft_summary, iteration.usage?.rune_draft),
    buildStageCard("카논 피드백", iteration.feedback, iteration.feedback_summary, iteration.usage?.canon),
    buildStageCard("에코 댓글", iteration.comment, iteration.comment_summary, iteration.usage?.echo),
    buildStageCard("최종본", iteration.final, iteration.final_summary, iteration.usage?.rune_final, true),
  ].join("");

  els.iterationFocus.innerHTML = `
    <div class="focus-header">
      <div>
        <p class="eyebrow">Selected Loop</p>
        <h3>Loop ${iteration.loop_index}</h3>
        <p class="workflow-meta">${escapeHtml(describeIterationState(iteration))}</p>
      </div>
      <div class="focus-meta">
        ${buildMetaPills([
          formatQualityLabel(iteration.quality),
          iteration.history_file ? `history ${iteration.history_file}` : "저장 전",
          formatPromptVersions(iteration.prompts) || "prompt meta 없음",
          formatUsageSummary(iteration.usage_summary),
        ])}
      </div>
    </div>

    <div class="stage-grid">
      ${stageCards}
    </div>

    <div class="compare-grid">
      <article class="detail-card canon-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Canon</p>
            <h3>설정 / 구조 점검</h3>
          </div>
          <span class="tone-badge ${canonTone(iteration.quality)}">${canonToneLabel(iteration.quality)}</span>
        </div>
        ${renderCanonFeedback(iteration.feedback, iteration.feedback_structured, "카논 코멘트가 아직 없습니다.")}
      </article>

      <article class="detail-card echo-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Echo</p>
            <h3>재미 / 몰입 반응</h3>
          </div>
          <span class="tone-badge ${echoTone(iteration.quality)}">${echoToneLabel(iteration.quality)}</span>
        </div>
        ${renderEchoComment(
          iteration.comment,
          iteration.comment_structured,
          "에코 반응이 아직 없습니다."
        )}
      </article>
    </div>

    ${renderFeedbackComparison(iteration.feedback, iteration.comment)}

    <div class="detail-grid">
      <article class="detail-card quality-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Quality</p>
            <h3>종료 판단 근거</h3>
          </div>
          <strong class="quality-score">${formatScore(iteration.quality)}</strong>
        </div>
        ${renderReasonList(iteration.quality)}
      </article>

      <article class="detail-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Connection</p>
            <h3>초안과 최종본의 연결</h3>
          </div>
        </div>
        <div class="connection-copy">
          <div class="connection-row">
            <span>초안 요약</span>
            <strong>${escapeHtml(iteration.draft_summary || "대기 중")}</strong>
          </div>
          <div class="connection-row">
            <span>최종본 요약</span>
            <strong>${escapeHtml(iteration.final_summary || "대기 중")}</strong>
          </div>
          <div class="connection-row">
            <span>카논 키워드</span>
            <strong>${escapeHtml(joinKeyPoints(iteration.feedback))}</strong>
          </div>
          <div class="connection-row">
            <span>에코 키워드</span>
            <strong>${escapeHtml(joinKeyPoints(iteration.comment))}</strong>
          </div>
        </div>
      </article>
    </div>
  `;
}

function buildStageCard(label, content, summary, usage, emphasized = false) {
  return `
    <article class="detail-card ${emphasized ? "emphasized" : ""}">
      <div class="detail-card-header">
        <div>
          <p class="eyebrow">${escapeHtml(label)}</p>
          <h3>${escapeHtml(summary || "아직 비어 있습니다.")}</h3>
        </div>
        <span class="token-pill">${escapeHtml(formatUsage(usage))}</span>
      </div>
      <div class="detail-copy">${escapeHtml(content || "아직 비어 있습니다.")}</div>
    </article>
  `;
}

function renderReflectionSummary(iteration) {
  if (!iteration || !iteration.final) {
    els.reflectionSummary.innerHTML = `<div class="empty-state">선택된 루프의 최종본이 생기면 반영 흔적이 표시됩니다.</div>`;
    return;
  }

  const items = [
    ...analyzeReflection(iteration.final, iteration.feedback, "카논"),
    ...analyzeReflection(iteration.final, iteration.comment, "에코"),
  ];

  if (!items.length) {
    els.reflectionSummary.innerHTML = `<div class="empty-state">비교할 피드백이 아직 없습니다.</div>`;
    return;
  }

  const reflected = items.filter((item) => item.status === "reflected").length;
  const partial = items.filter((item) => item.status === "partial").length;
  const missing = items.filter((item) => item.status === "missing").length;

  els.reflectionSummary.innerHTML = `
    <div class="reflection-header">
      <div>
        <p class="eyebrow">Reflection Trace</p>
        <h3>피드백 반영 흔적</h3>
        <p class="workflow-meta">문장 겹침과 키워드 일치를 기준으로 추정한 자동 분석입니다.</p>
      </div>
      <div class="focus-meta">
        ${buildMetaPills([`반영 ${reflected}`, `부분 ${partial}`, `약함 ${missing}`])}
      </div>
    </div>
    <div class="reflection-list">
      ${items
        .map(
          (item) => `
            <article class="reflection-item ${item.status}">
              <div class="reflection-item-top">
                <span class="meta-pill">${escapeHtml(item.source)}</span>
                <span class="tone-badge ${reflectionTone(item.status)}">${escapeHtml(reflectionLabel(item.status))}</span>
              </div>
              <strong>${escapeHtml(item.point)}</strong>
              <div class="reflection-foot">
                <span>${escapeHtml(item.note)}</span>
                <span>${escapeHtml(item.matchedLabel)}</span>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function analyzeReflection(finalText, sourceText, sourceLabel) {
  const points = extractKeyPoints(sourceText);
  if (!points.length) {
    return [];
  }

  const finalNormalized = normalizeSearchText(finalText);

  return points.slice(0, 4).map((point) => {
    const keywords = extractKeywords(point);
    const matched = keywords.filter((keyword) => finalNormalized.includes(normalizeSearchText(keyword)));
    let status = "missing";

    if (matched.length >= Math.min(2, keywords.length) && matched.length > 0) {
      status = "reflected";
    } else if (matched.length > 0) {
      status = "partial";
    }

    return {
      source: sourceLabel,
      point,
      status,
      note: reflectionNote(status),
      matchedLabel: matched.length ? `겹친 키워드: ${matched.join(", ")}` : "겹친 키워드 없음",
    };
  });
}

function bindIterationButtons() {
  document.querySelectorAll("[data-iteration]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedIteration = Number(button.dataset.iteration);
      renderLoopState(state.latestLoopState || { iterations: [] });
      setActiveView("workroom");
      renderViewSummaries();
    });
  });
}

function syncSelectedIteration(iterations, loopState) {
  if (!iterations.length) {
    state.selectedIteration = null;
    return;
  }

  const hasSelection = iterations.some((item) => item.loop_index === state.selectedIteration);
  if (hasSelection) {
    return;
  }

  const active = iterations.find((item) => item.loop_index === loopState.current_iteration);
  const latestResolved = [...iterations].reverse().find((item) => item.status !== "pending");
  state.selectedIteration = active?.loop_index || latestResolved?.loop_index || iterations[0].loop_index;
}

function getSelectedIteration(iterations) {
  if (!iterations.length) {
    return null;
  }
  return (
    iterations.find((item) => item.loop_index === state.selectedIteration) ||
    iterations[iterations.length - 1]
  );
}

function handleHistorySearch(event) {
  state.historyQuery = event.target.value.trim();
  renderHistory(state.latestHistory);
  renderViewSummaries();
}

function handleHistoryFilter(event) {
  state.historyFilter = event.target.value;
  renderHistory(state.latestHistory);
  renderViewSummaries();
}

function renderHistory(history) {
  state.latestHistory = history;
  const filtered = filterHistory(history);
  syncSelectedHistory(filtered);
  renderHistoryList(filtered);
  renderHistoryDetail(filtered.find((item) => item.filename === state.selectedHistoryFile) || null);
}

function filterHistory(history) {
  return history.filter((item) => {
    if (state.historyFilter === "stopped" && !item.quality?.should_stop) {
      return false;
    }
    if (state.historyFilter === "continue" && item.quality?.should_stop) {
      return false;
    }

    if (!state.historyQuery) {
      return true;
    }

    const target = [item.title, item.plot, item.outputs?.final, item.outputs?.feedback, item.outputs?.comment]
      .join(" ")
      .toLowerCase();

    return target.includes(state.historyQuery.toLowerCase());
  });
}

function syncSelectedHistory(history) {
  if (!history.length) {
    state.selectedHistoryFile = null;
    return;
  }

  const hasSelection = history.some((item) => item.filename === state.selectedHistoryFile);
  if (!hasSelection) {
    state.selectedHistoryFile = history[0].filename;
  }
}

function renderHistoryList(history) {
  if (!history.length) {
    els.historyList.innerHTML = `<div class="empty-state">조건에 맞는 결과물이 없습니다.</div>`;
    return;
  }

  els.historyList.innerHTML = history
    .map((item) => {
      const selected = item.filename === state.selectedHistoryFile;
      const quality = item.quality || {};
      return `
        <button
          type="button"
          class="history-card ${selected ? "selected" : ""}"
          data-history-file="${item.filename}"
        >
          <div class="history-card-top">
            <h3>${escapeHtml(item.title || "untitled")}</h3>
            <span class="history-badge ${quality.should_stop ? "good" : "open"}">
              ${quality.should_stop ? "조기 종료" : "추가 루프 가능"}
            </span>
          </div>
          <div class="history-meta">
            ${escapeHtml(item.created_at || "")}<br />
            Loop ${item.loop_index || 0} · ${escapeHtml(formatPromptVersions(item.prompts) || "prompt meta 없음")}<br />
            ${escapeHtml(trimText(item.outputs?.final || "", 120))}
          </div>
        </button>
      `;
    })
    .join("");

  bindHistoryButtons();
}

function renderHistoryDetail(item) {
  if (!item) {
    els.historyDetail.innerHTML = `<div class="empty-state">저장된 결과물을 선택하면 상세가 열립니다.</div>`;
    return;
  }

  els.historyDetail.innerHTML = `
    <div class="focus-header">
      <div>
        <p class="eyebrow">Selected History</p>
        <h3>${escapeHtml(item.title || "untitled")}</h3>
      </div>
      <div class="focus-meta">
        ${buildMetaPills([
          item.created_at || "",
          `Loop ${item.loop_index || 0}`,
          formatQualityLabel(item.quality),
          formatUsageSummary(item.usage_summary),
        ])}
      </div>
    </div>

    <div class="history-detail-grid">
      <article class="detail-card emphasized">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Final</p>
            <h3>저장된 최종본</h3>
          </div>
        </div>
        <div class="detail-copy">${escapeHtml(item.outputs?.final || "최종본이 없습니다.")}</div>
      </article>

      <article class="detail-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Plot</p>
            <h3>입력 플롯</h3>
          </div>
        </div>
        <div class="detail-copy">${escapeHtml(item.plot || "플롯 정보가 없습니다.")}</div>
      </article>
    </div>

    <div class="compare-grid">
      <article class="detail-card canon-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Canon</p>
            <h3>저장된 피드백</h3>
          </div>
        </div>
        ${renderCanonFeedback(item.outputs?.feedback || "", item.feedback_structured, "카논 피드백이 없습니다.")}
      </article>

      <article class="detail-card echo-card">
        <div class="detail-card-header">
          <div>
            <p class="eyebrow">Echo</p>
            <h3>저장된 댓글</h3>
          </div>
        </div>
        ${renderEchoComment(
          item.outputs?.comment || "",
          item.comment_structured,
          "에코 댓글이 없습니다."
        )}
      </article>
    </div>

    ${renderFeedbackComparison(item.outputs?.feedback || "", item.outputs?.comment || "")}
  `;
}

function bindHistoryButtons() {
  document.querySelectorAll("[data-history-file]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedHistoryFile = button.dataset.historyFile;
      renderHistory(state.latestHistory);
      setActiveView("archive");
      renderViewSummaries();
    });
  });
}

function renderSilLog(entries) {
  state.latestSilLog = entries;

  if (!entries.length) {
    els.silLogList.innerHTML = `<div class="empty-state">Sil 로그가 아직 없습니다.</div>`;
    return;
  }

  const latest = entries[entries.length - 1];
  if (state.initialized && latest.timestamp !== state.lastSilTimestamp && latest.kind === "error") {
    triggerSilhouette();
  }
  state.lastSilTimestamp = latest.timestamp;

  els.silLogList.innerHTML = [...entries]
    .reverse()
    .map(
      (entry) => `
        <article class="sil-log-item ${escapeHtml(entry.kind || "")}">
          <div>${escapeHtml(entry.display || "")}</div>
          ${entry.epilogue ? `<div>${escapeHtml(entry.epilogue)}</div>` : ""}
        </article>
      `
    )
    .join("");
}

function renderViewSummaries() {
  const loopState = state.latestLoopState || { iterations: [], cards: [], config: {} };
  const messageCount = buildChatMessages(loopState).length;
  const selected = getSelectedIteration(loopState.iterations || []);
  const historyCount = state.latestHistory.length;
  const silCount = state.latestSilLog.length;

  els.viewSummaryMain.textContent = loopState.plot
    ? `메시지 ${messageCount}개 · ${loopState.stage || "idle"} · ${loopState.current_iteration || 0}회차`
    : "현재 루프의 대화와 첨부 파일이 여기 모입니다.";

  els.viewSummaryWorkroom.textContent = selected
    ? `선택 루프 ${selected.loop_index} · ${selected.status || "pending"} · ${selected.final_summary || selected.draft_summary || "대기 중"}`
    : "설정, 세부 실행 옵션, 루프 상세를 정리합니다.";

  els.viewSummaryArchive.textContent =
    historyCount || silCount
      ? `결과물 ${historyCount}개 · Sil ${silCount}건`
      : "히스토리와 Sil 로그를 따로 봅니다.";
}

async function refreshLivePanels() {
  const [loopState, history, silLog] = await Promise.all([
    api("/api/loop-state"),
    api("/api/history"),
    api("/api/sil-log"),
  ]);
  renderLoopState(loopState);
  renderHistory(history);
  renderSilLog(silLog);
  renderViewSummaries();
}

function syncPolling(loopState) {
  const shouldPoll = loopState.status === "running";
  window.clearInterval(state.pollingTimer);
  if (!shouldPoll) {
    return;
  }

  state.pollingTimer = window.setInterval(async () => {
    try {
      const current = await api("/api/loop-state");
      renderLoopState(current);
      const [history, silLog] = await Promise.all([api("/api/history"), api("/api/sil-log")]);
      renderHistory(history);
      renderSilLog(silLog);
      renderViewSummaries();
      if (current.status !== "running") {
        window.clearInterval(state.pollingTimer);
      }
    } catch (error) {
      showNotice(error.message, true);
      window.clearInterval(state.pollingTimer);
    }
  }, 2500);
}

function renderPersonaActivation(activePersona) {
  const activeSet = new Set(
    activePersona === "canon_echo"
      ? ["canon", "echo"]
      : activePersona
        ? [activePersona]
        : []
  );

  [
    ["rune", els.personaRune],
    ["canon", els.personaCanon],
    ["echo", els.personaEcho],
    ["sil", els.personaSil],
  ].forEach(([key, element]) => {
    element.classList.toggle("active", activeSet.has(key));
  });
}

function exportSelectedIteration(format) {
  const loopState = state.latestLoopState;
  const iteration = getSelectedIteration(loopState?.iterations || []);
  if (!loopState || !iteration) {
    showNotice("내보낼 루프가 아직 없습니다.", true);
    return;
  }

  const payload = buildIterationExportPayload(loopState, iteration);
  const filenameBase = buildFileSlug(loopState.title || `loop_${iteration.loop_index}`);
  if (format === "json") {
    downloadFile(
      `${filenameBase}_selected-loop.json`,
      `${JSON.stringify(payload, null, 2)}\n`,
      "application/json;charset=utf-8"
    );
    showNotice("선택된 루프를 JSON으로 내보냈습니다.");
    return;
  }

  downloadFile(
    `${filenameBase}_selected-loop.md`,
    renderIterationMarkdown(payload),
    "text/markdown;charset=utf-8"
  );
  showNotice("선택된 루프를 Markdown으로 내보냈습니다.");
}

function exportSelectedHistory(format) {
  const item = getSelectedHistory();
  if (!item) {
    showNotice("내보낼 결과물이 없습니다.", true);
    return;
  }

  const filenameBase = buildFileSlug(item.title || item.filename || "history");
  if (format === "json") {
    downloadFile(
      `${filenameBase}.json`,
      `${JSON.stringify(item, null, 2)}\n`,
      "application/json;charset=utf-8"
    );
    showNotice("선택된 결과물을 JSON으로 내보냈습니다.");
    return;
  }

  downloadFile(
    `${filenameBase}.md`,
    renderHistoryMarkdown(item),
    "text/markdown;charset=utf-8"
  );
  showNotice("선택된 결과물을 Markdown으로 내보냈습니다.");
}

function getSelectedHistory() {
  return state.latestHistory.find((item) => item.filename === state.selectedHistoryFile) || null;
}

function buildIterationExportPayload(loopState, iteration) {
  return {
    run_id: loopState.run_id,
    title: loopState.title,
    plot: loopState.plot,
    stage: loopState.stage,
    status: loopState.status,
    config: loopState.config,
    usage_summary: loopState.usage_summary,
    iteration: {
      loop_index: iteration.loop_index,
      status: iteration.status,
      summary: {
        draft: iteration.draft_summary,
        feedback: iteration.feedback_summary,
        comment: iteration.comment_summary,
        final: iteration.final_summary,
      },
      outputs: {
        draft: iteration.draft,
        feedback: iteration.feedback,
        comment: iteration.comment,
        final: iteration.final,
      },
      feedback_structured: iteration.feedback_structured,
      comment_structured: iteration.comment_structured,
      quality: iteration.quality,
      prompts: iteration.prompts,
      usage: iteration.usage,
      usage_summary: iteration.usage_summary,
      history_file: iteration.history_file,
    },
  };
}

function renderIterationMarkdown(payload) {
  const iteration = payload.iteration;
  return [
    `# ${payload.title || "Untitled"}`,
    "",
    `- Run ID: ${payload.run_id || "-"}`,
    `- Loop: ${iteration.loop_index}`,
    `- Status: ${iteration.status || "-"}`,
    `- Stage: ${payload.stage || "-"}`,
    `- Quality: ${formatQualityLabel(iteration.quality)}`,
    `- Run Usage: ${formatUsageSummary(payload.usage_summary) || "-"}`,
    `- Loop Usage: ${formatUsageSummary(iteration.usage_summary) || "-"}`,
    "",
    "## Plot",
    "",
    payload.plot || "",
    "",
    "## Draft",
    "",
    iteration.outputs.draft || "",
    "",
    "## Canon Feedback",
    "",
    iteration.outputs.feedback || "",
    "",
    "## Echo Comment",
    "",
    iteration.outputs.comment || "",
    "",
    "## Final",
    "",
    iteration.outputs.final || "",
    "",
    "## Prompt Versions",
    "",
    formatPromptVersions(iteration.prompts) || "-",
    "",
    "## Quality Reasons",
    "",
    ...(iteration.quality?.reasons?.map((reason) => `- ${reason}`) || ["-"]),
    "",
  ].join("\n");
}

function renderHistoryMarkdown(item) {
  return [
    `# ${item.title || "Untitled"}`,
    "",
    `- Created At: ${item.created_at || "-"}`,
    `- Loop: ${item.loop_index || "-"}`,
    `- Quality: ${formatQualityLabel(item.quality)}`,
    `- Prompt Versions: ${formatPromptVersions(item.prompts) || "-"}`,
    `- Usage: ${formatUsageSummary(item.usage_summary) || "-"}`,
    "",
    "## Plot",
    "",
    item.plot || "",
    "",
    "## Draft",
    "",
    item.outputs?.draft || "",
    "",
    "## Canon Feedback",
    "",
    item.outputs?.feedback || "",
    "",
    "## Echo Comment",
    "",
    item.outputs?.comment || "",
    "",
    "## Final",
    "",
    item.outputs?.final || "",
    "",
    "## Quality Reasons",
    "",
    ...(item.quality?.reasons?.map((reason) => `- ${reason}`) || ["-"]),
    "",
  ].join("\n");
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function buildFileSlug(value) {
  return (
    String(value || "export")
      .trim()
      .replace(/[<>:"/\\|?*]+/g, "_")
      .replace(/\s+/g, "_")
      .slice(0, 48) || "export"
  );
}

function renderInsightList(text, emptyText) {
  const items = extractKeyPoints(text);
  if (!items.length) {
    return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
  }

  return `
    <div class="insight-list">
      ${items.map((item) => `<div class="insight-item">${escapeHtml(item)}</div>`).join("")}
    </div>
  `;
}

function renderCanonFeedback(text, structured, emptyText) {
  const normalized = normalizeStructuredCanonFeedback(text, structured);
  if (!normalized) {
    return renderInsightList(text, emptyText);
  }

  const verdictTone = normalized.verdict === "ok" ? "stable" : "alert";
  return `
    <section class="structured-feedback">
      <div class="structured-feedback-top">
        <span class="meta-pill">판정</span>
        <span class="tone-badge ${verdictTone}">${escapeHtml(normalized.verdictLabel)}</span>
      </div>
      <div class="structured-feedback-grid">
        ${Object.entries(normalized.sections)
          .map(([key, section]) => renderCanonSection(key, section))
          .join("")}
      </div>
    </section>
  `;
}

function renderEchoComment(text, structured, emptyText) {
  const normalized = normalizeStructuredEchoComment(text, structured);
  if (!normalized) {
    return renderInsightList(text, emptyText);
  }

  return `
    <section class="structured-feedback">
      <div class="structured-feedback-grid">
        ${["reaction", "immersion", "dropoff"]
          .map((key) => renderEchoSection(key, normalized.sections[key]))
          .join("")}
      </div>
    </section>
  `;
}

function normalizeStructuredCanonFeedback(text, structured) {
  if (structured && structured.sections) {
    return {
      verdict: structured.verdict || "revise",
      verdictLabel: structured.verdict_label || (structured.verdict === "ok" ? "이상 없음" : "수정 필요"),
      sections: structured.sections,
    };
  }
  return parseStructuredCanonFeedback(text);
}

function normalizeStructuredEchoComment(text, structured) {
  if (structured && structured.sections) {
    return {
      sections: {
        reaction: structured.sections.reaction || [],
        immersion: structured.sections.immersion || [],
        dropoff: structured.sections.dropoff || [],
      },
    };
  }
  return parseStructuredEchoComment(text);
}

function parseStructuredCanonFeedback(text) {
  const lines = String(text || "")
    .replace(/^\[[^\]]+\]\s*/gm, "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.some((line) => line.startsWith("판정:"))) {
    return null;
  }

  const labelMap = {
    "설정": "setting",
    "구조": "structure",
    "미래 리스크": "future_risk",
    "다음 액션": "next_action",
  };
  const sections = {
    setting: [],
    structure: [],
    future_risk: [],
    next_action: [],
  };
  let verdict = "revise";
  let verdictLabel = "수정 필요";
  let currentKey = null;

  lines.forEach((line) => {
    if (line.startsWith("판정:")) {
      verdictLabel = line.replace("판정:", "").trim() || "수정 필요";
      verdict = verdictLabel.includes("이상 없음") ? "ok" : "revise";
      return;
    }

    if (line.endsWith(":")) {
      const label = line.slice(0, -1);
      currentKey = labelMap[label] || null;
      return;
    }

    if (!currentKey) {
      return;
    }

    sections[currentKey].push(line.replace(/^[-*•]\s*/, "").trim());
  });

  if (!Object.values(sections).some((items) => items.length)) {
    return null;
  }

  return { verdict, verdictLabel, sections };
}

function parseStructuredEchoComment(text) {
  const lines = String(text || "")
    .replace(/^\[[^\]]+\]\s*/gm, "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.some((line) => line.startsWith("반응:") || line.startsWith("몰입:") || line.startsWith("이탈감:"))) {
    return null;
  }

  const labelMap = {
    "반응": "reaction",
    "몰입": "immersion",
    "이탈감": "dropoff",
  };
  const sections = {
    reaction: [],
    immersion: [],
    dropoff: [],
  };
  let currentKey = null;

  lines.forEach((line) => {
    const directMatch =
      Object.entries(labelMap).find(([label]) => line.startsWith(`${label}:`)) || null;
    if (directMatch) {
      currentKey = directMatch[1];
      const remainder = line.slice(directMatch[0].length + 1).trim();
      if (remainder) {
        sections[currentKey].push(remainder);
      }
      return;
    }

    if (line.endsWith(":")) {
      currentKey = labelMap[line.slice(0, -1)] || null;
      return;
    }

    if (!currentKey) {
      return;
    }

    sections[currentKey].push(line.replace(/^[-*•]\s*/, "").trim());
  });

  if (!Object.values(sections).some((items) => items.length)) {
    return null;
  }

  return { sections };
}

function renderCanonSection(key, items) {
  const title = {
    setting: "설정",
    structure: "구조",
    future_risk: "미래 리스크",
    next_action: "다음 액션",
  }[key] || key;
  return renderStructuredFeedbackSection(title, items);
}

function renderEchoSection(key, items) {
  const title = {
    reaction: "반응",
    immersion: "몰입",
    dropoff: "이탈감",
  }[key] || key;
  return renderStructuredFeedbackSection(title, items);
}

function renderStructuredFeedbackSection(title, items) {
  const safeItems = items && items.length ? items : ["없음"];
  return `
    <article class="structured-section">
      <p class="eyebrow">${escapeHtml(title)}</p>
      <div class="insight-list compact">
        ${safeItems
          .map((item) => `<div class="insight-item compact">${escapeHtml(item)}</div>`)
          .join("")}
      </div>
    </article>
  `;
}

function renderFeedbackComparison(canonText, echoText) {
  const comparison = analyzeFeedbackComparison(canonText, echoText);
  if (!comparison.hasContent) {
    return `
      <section class="comparison-summary">
        <div class="empty-state">카논과 에코의 의견이 쌓이면 자동 비교가 열립니다.</div>
      </section>
    `;
  }

  return `
    <section class="comparison-summary">
      <div class="reflection-header">
        <div>
          <p class="eyebrow">Comparison</p>
          <h3>카논 / 에코 비교</h3>
          <p class="workflow-meta">겹친 키워드와 어조 차이를 기준으로 자동 정리한 비교입니다.</p>
        </div>
        <div class="focus-meta">
          ${buildMetaPills([
            `겹침 ${comparison.aligned.length}`,
            `긴장 ${comparison.tension.length}`,
            `카논만 ${comparison.canonOnly.length}`,
            `에코만 ${comparison.echoOnly.length}`,
          ])}
        </div>
      </div>

      <div class="comparison-columns">
        ${renderComparisonCard({
          eyebrow: "Shared",
          title: "같이 본 지점",
          toneClass: "stable",
          toneLabel: comparison.aligned.length ? "겹친 시선" : "겹침 없음",
          cardClass: "aligned",
          emptyText: "같은 키워드로 맞물린 지점이 아직 없습니다.",
          items: comparison.aligned.map((item) => renderComparisonPair(item)),
        })}
        ${renderComparisonCard({
          eyebrow: "Tension",
          title: "긴장 지점",
          toneClass: "alert",
          toneLabel: comparison.tension.length ? "해석 갈림" : "긴장 없음",
          cardClass: "tension",
          emptyText: "같은 주제를 두고 해석이 갈린 지점은 아직 없습니다.",
          items: comparison.tension.map((item) => renderComparisonPair(item)),
        })}
        ${renderComparisonCard({
          eyebrow: "Canon",
          title: "카논만 본 지점",
          toneClass: "neutral",
          toneLabel: comparison.canonOnly.length ? "구조 시선" : "없음",
          cardClass: "canon",
          emptyText: "카논만 별도로 짚은 지점은 아직 없습니다.",
          items: comparison.canonOnly.map((item) => renderComparisonSolo(item, "canon")),
        })}
        ${renderComparisonCard({
          eyebrow: "Echo",
          title: "에코만 본 지점",
          toneClass: "positive",
          toneLabel: comparison.echoOnly.length ? "독자 시선" : "없음",
          cardClass: "echo",
          emptyText: "에코만 별도로 반응한 지점은 아직 없습니다.",
          items: comparison.echoOnly.map((item) => renderComparisonSolo(item, "echo")),
        })}
      </div>
    </section>
  `;
}

function renderComparisonCard({
  eyebrow,
  title,
  toneClass,
  toneLabel,
  cardClass,
  emptyText,
  items,
}) {
  return `
    <article class="detail-card comparison-card ${cardClass}">
      <div class="detail-card-header">
        <div>
          <p class="eyebrow">${escapeHtml(eyebrow)}</p>
          <h3>${escapeHtml(title)}</h3>
        </div>
        <span class="tone-badge ${toneClass}">${escapeHtml(toneLabel)}</span>
      </div>
      ${
        items.length
          ? `<div class="comparison-list">${items.join("")}</div>`
          : `<div class="empty-state">${escapeHtml(emptyText)}</div>`
      }
    </article>
  `;
}

function renderComparisonPair(item) {
  return `
    <article class="comparison-item ${item.relationship}">
      <div class="comparison-item-top">
        <span class="meta-pill">${escapeHtml(formatMatchedKeywords(item.matchedKeywords))}</span>
        <span class="tone-badge ${comparisonRelationshipTone(item.relationship)}">${escapeHtml(comparisonRelationshipLabel(item.relationship, item.canonPoint.tone, item.echoPoint.tone))}</span>
      </div>
      <div class="comparison-copy">
        <strong>카논</strong>
        <span>${escapeHtml(item.canonPoint.point)}</span>
      </div>
      <div class="comparison-copy">
        <strong>에코</strong>
        <span>${escapeHtml(item.echoPoint.point)}</span>
      </div>
      <div class="comparison-foot">${escapeHtml(comparisonPairNote(item))}</div>
    </article>
  `;
}

function renderComparisonSolo(item, source) {
  return `
    <article class="comparison-item ${escapeHtml(source)}">
      <div class="comparison-item-top">
        <span class="meta-pill">${escapeHtml(formatPointKeywords(item.keywords))}</span>
        <span class="tone-badge ${comparisonSoloTone(source, item.tone)}">${escapeHtml(comparisonSoloLabel(source, item.tone))}</span>
      </div>
      <div class="comparison-copy">
        <strong>${source === "canon" ? "카논" : "에코"}</strong>
        <span>${escapeHtml(item.point)}</span>
      </div>
      <div class="comparison-foot">${escapeHtml(comparisonSoloNote(source, item.tone))}</div>
    </article>
  `;
}

function analyzeFeedbackComparison(canonText, echoText) {
  const canonPoints = buildComparablePoints(canonText, "canon");
  const echoPoints = buildComparablePoints(echoText, "echo");
  const usedCanon = new Set();
  const usedEcho = new Set();
  const candidates = [];

  canonPoints.forEach((canonPoint, canonIndex) => {
    echoPoints.forEach((echoPoint, echoIndex) => {
      const matchedKeywords = canonPoint.keywords.filter((keyword) => echoPoint.keywords.includes(keyword));
      if (!matchedKeywords.length) {
        return;
      }
      candidates.push({
        canonIndex,
        echoIndex,
        matchedKeywords,
        overlapScore: matchedKeywords.length,
      });
    });
  });

  candidates.sort((left, right) => right.overlapScore - left.overlapScore);

  const aligned = [];
  const tension = [];
  candidates.forEach((candidate) => {
    if (usedCanon.has(candidate.canonIndex) || usedEcho.has(candidate.echoIndex)) {
      return;
    }

    usedCanon.add(candidate.canonIndex);
    usedEcho.add(candidate.echoIndex);

    const canonPoint = canonPoints[candidate.canonIndex];
    const echoPoint = echoPoints[candidate.echoIndex];
    const relationship = classifyComparisonRelationship(canonPoint.tone, echoPoint.tone);
    const entry = {
      canonPoint,
      echoPoint,
      matchedKeywords: candidate.matchedKeywords,
      relationship,
    };

    if (relationship === "tension") {
      tension.push(entry);
      return;
    }
    aligned.push(entry);
  });

  return {
    hasContent: Boolean(canonPoints.length || echoPoints.length),
    aligned,
    tension,
    canonOnly: canonPoints.filter((_, index) => !usedCanon.has(index)),
    echoOnly: echoPoints.filter((_, index) => !usedEcho.has(index)),
  };
}

function buildComparablePoints(text, source) {
  return extractKeyPoints(text)
    .slice(0, 4)
    .map((point) => ({
      point,
      source,
      keywords: extractKeywords(point),
      tone: detectPointTone(point, source),
    }))
    .filter((item) => item.point);
}

function detectPointTone(text, source) {
  const normalized = normalizeSearchText(text);
  const positiveScore =
    scoreSignalMatches(normalized, POSITIVE_SIGNAL_PATTERNS) +
    scoreSignalMatches(
      normalized,
      source === "echo" ? ECHO_POSITIVE_SIGNAL_PATTERNS : CANON_POSITIVE_SIGNAL_PATTERNS
    );
  const concernScore =
    scoreSignalMatches(normalized, CONCERN_SIGNAL_PATTERNS) +
    scoreSignalMatches(
      normalized,
      source === "echo" ? ECHO_CONCERN_SIGNAL_PATTERNS : CANON_CONCERN_SIGNAL_PATTERNS
    );

  if (positiveScore > concernScore && positiveScore > 0) {
    return "positive";
  }
  if (concernScore > 0) {
    return "concern";
  }
  return "neutral";
}

function scoreSignalMatches(text, patterns) {
  return patterns.reduce((score, pattern) => score + (text.includes(pattern) ? 1 : 0), 0);
}

function classifyComparisonRelationship(canonTone, echoTone) {
  const tones = [canonTone, echoTone];
  return tones.includes("positive") && tones.includes("concern") ? "tension" : "aligned";
}

function comparisonRelationshipTone(relationship) {
  return relationship === "tension" ? "alert" : "stable";
}

function comparisonRelationshipLabel(relationship, canonTone, echoTone) {
  if (relationship === "tension") {
    if (canonTone === "concern" && echoTone === "positive") {
      return "매력 vs 리스크";
    }
    if (canonTone === "positive" && echoTone === "concern") {
      return "구조 통과 vs 반응 약함";
    }
    return "해석 갈림";
  }
  if (canonTone === "positive" && echoTone === "positive") {
    return "같이 호응";
  }
  if (canonTone === "concern" && echoTone === "concern") {
    return "같이 경고";
  }
  return "같은 축";
}

function comparisonPairNote(item) {
  if (item.relationship === "tension") {
    if (item.canonPoint.tone === "concern" && item.echoPoint.tone === "positive") {
      return "독자 반응은 살아 있지만 카논은 같은 축에서 구조 리스크를 보고 있습니다.";
    }
    if (item.canonPoint.tone === "positive" && item.echoPoint.tone === "concern") {
      return "카논은 통과시켰지만 에코는 같은 축에서 몰입 저하를 느끼고 있습니다.";
    }
    return "같은 키워드를 두고 읽는 방향이 갈린 지점입니다.";
  }
  if (item.canonPoint.tone === "positive" && item.echoPoint.tone === "positive") {
    return "카논과 에코가 모두 강점으로 읽은 지점입니다.";
  }
  if (item.canonPoint.tone === "concern" && item.echoPoint.tone === "concern") {
    return "카논과 에코가 모두 손봐야 할 지점으로 본 부분입니다.";
  }
  return "같은 키워드 축에서 읽힌 지점입니다.";
}

function comparisonSoloTone(source, tone) {
  if (tone === "concern") {
    return "alert";
  }
  if (source === "echo" || tone === "positive") {
    return "positive";
  }
  return "neutral";
}

function comparisonSoloLabel(source, tone) {
  if (source === "canon") {
    return tone === "concern" ? "구조 경고" : "구조 시선";
  }
  return tone === "concern" ? "이질감" : "독자 반응";
}

function comparisonSoloNote(source, tone) {
  if (source === "canon") {
    return tone === "concern"
      ? "카논만 명시적으로 짚은 설정/구조 리스크입니다."
      : "카논 쪽에서만 별도로 강조한 설정/구조 포인트입니다.";
  }
  return tone === "concern"
    ? "에코만 감각적으로 불편함이나 이질감을 느낀 지점입니다."
    : "에코만 독자 반응으로 먼저 집어낸 지점입니다.";
}

function formatMatchedKeywords(keywords) {
  return keywords.length ? `겹친 키워드: ${keywords.join(", ")}` : "겹친 키워드 없음";
}

function formatPointKeywords(keywords) {
  return keywords.length ? `키워드: ${keywords.join(", ")}` : "키워드 추출 없음";
}

function renderReasonList(quality) {
  const reasons = quality?.reasons || [];
  if (!reasons.length) {
    return `<div class="empty-state">판단 근거가 아직 없습니다.</div>`;
  }

  return `
    <div class="reason-list">
      ${reasons.map((reason) => `<div class="reason-item">${escapeHtml(reason)}</div>`).join("")}
    </div>
  `;
}

function describeIterationState(iteration) {
  const parts = [`상태 ${iteration.status || "pending"}`];
  if (iteration.feedback || iteration.comment) {
    parts.push("리뷰 완료");
  }
  if (iteration.final) {
    parts.push("최종본 생성");
  }
  return parts.join(" · ");
}

function showNotice(message, isError = false) {
  els.systemNotice.textContent = message;
  els.systemNotice.style.color = isError ? "#d48c8c" : "";
}

function setBusy(button, busy) {
  button.disabled = busy;
  if (button === els.runButton) {
    button.textContent = busy ? "루프 진행 중..." : "루프 시작";
  }
  if (button === els.cancelButton) {
    button.textContent = busy ? "취소 요청 중..." : "루프 취소";
  }
  if (button === els.estimateButton) {
    button.textContent = busy ? "계산 중..." : "비용 추정";
  }
}

function syncRunControls(loopState) {
  const status = loopState?.status || "idle";
  const isRunning = status === "running";
  els.runButton.disabled = isRunning;
  els.cancelButton.disabled = !isRunning;
  if (!isRunning) {
    els.runButton.textContent = "루프 시작";
  }
  els.cancelButton.textContent = isRunning ? "루프 취소" : "취소 대기";
}

function triggerSilhouette() {
  els.silhouette.classList.add("visible");
  window.setTimeout(() => {
    els.silhouette.classList.remove("visible");
  }, 2200);
}

function buildMetaPills(items) {
  return items
    .filter(Boolean)
    .map((item) => `<span class="meta-pill">${escapeHtml(item)}</span>`)
    .join("");
}

function canonTone(quality) {
  if (!quality) {
    return "neutral";
  }
  return quality.canon_clean ? "stable" : "alert";
}

function canonToneLabel(quality) {
  if (!quality) {
    return "판단 대기";
  }
  return quality.canon_clean ? "설정 안정" : "수정 필요";
}

function echoTone(quality) {
  if (!quality) {
    return "neutral";
  }
  return quality.echo_positive ? "positive" : "alert";
}

function echoToneLabel(quality) {
  if (!quality) {
    return "판단 대기";
  }
  return quality.echo_positive ? "호응 우세" : "이질감 경고";
}

function reflectionTone(status) {
  return {
    reflected: "stable",
    partial: "positive",
    missing: "alert",
  }[status] || "neutral";
}

function reflectionLabel(status) {
  return {
    reflected: "반영 흔적 뚜렷",
    partial: "부분 반영",
    missing: "직접 흔적 약함",
  }[status] || "판단 대기";
}

function reflectionNote(status) {
  return {
    reflected: "최종본에서 피드백 키워드가 비교적 또렷하게 보입니다.",
    partial: "일부 키워드는 보이지만 직접 대응은 약합니다.",
    missing: "최종본에서 바로 읽히는 대응 표현은 적습니다.",
  }[status] || "판단 대기";
}

function getPersonaLines(affinityStage) {
  const map = {
    distant: {
      rune: "이야기가 나를 쓰는 건지, 내가 이야기를 쓰는 건지 모르겠어요.",
      canon: "아직 일어나지 않은 일을 알기에, 더 정확해야 해요.",
      echo: "재미없으면 바로 말할 거야. 근데 좋으면 진짜 좋아할 거고.",
      sil: "[대기 중] 이상 없음.",
    },
    warm: {
      rune: "이번엔 조금 더 끝까지 써볼 수 있을 것 같아요.",
      canon: "미래를 알고 있어도, 지금 장면은 함께 붙들 수 있습니다.",
      echo: "좋은 장면 나오면 나 진짜 크게 반응할 준비돼 있음.",
      sil: "[대기 중] 균열 감시 중.",
    },
    close: {
      rune: "저자가 돌아오면 문장이 덜 흔들려요.",
      canon: "이제는 어디를 눌러야 이야기가 더 선명해지는지 압니다.",
      echo: "이번 건 진짜 기대 중이야. 얼른 보여 줘.",
      sil: "[대기 중] 실 정렬 완료.",
    },
  };
  return map[affinityStage] || map.distant;
}

function labelForPersona(persona) {
  return {
    rune_draft: "루네 초안",
    canon_review: "카논 피드백",
    echo_comment: "에코 댓글",
    rune_final: "루네 최종본",
  }[persona] || persona;
}

function formatPromptVersions(prompts) {
  if (!prompts || typeof prompts !== "object") {
    return "";
  }

  return Object.entries(prompts)
    .filter(([, meta]) => meta && meta.version)
    .map(([key, meta]) => `${labelForPersona(key)} ${meta.version}`)
    .join(" · ");
}

function cardLabel(status) {
  return {
    pending: "숨 고르기",
    active: "뒤집히는 중",
    done: "보존 완료",
    skipped: "잠시 봉인",
    cancelled: "중단 보관",
  }[status] || "대기";
}

function formatUsage(usage) {
  if (!usage || typeof usage !== "object") {
    return "usage 없음";
  }
  const total = Number(usage.total_tokens || 0);
  if (!total) {
    return "usage 없음";
  }
  const approximate = Boolean(usage.approximate) || usage.source === "mock";
  const cost = Number(usage.total_cost_usd || 0);
  if (cost > 0) {
    return `${formatNumber(total)} tokens · ${formatUsd(cost, approximate)}`;
  }
  return `${formatNumber(total)} tokens`;
}

function formatUsageSummary(summary) {
  if (!summary || typeof summary !== "object") {
    return "";
  }
  const total = Number(summary.total_tokens || 0);
  if (!total) {
    return "";
  }
  const cost = Number(summary.total_cost_usd || 0);
  const approximate = Boolean(summary.approximate);
  if (cost > 0) {
    return `${formatNumber(total)} tokens · ${formatUsd(cost, approximate)}`;
  }
  return `${formatNumber(total)} tokens`;
}

function formatUsd(value, approximate = false) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount) || amount <= 0) {
    return "$0.0000";
  }
  const prefix = approximate ? "약 " : "";
  return `${prefix}$${amount.toFixed(4)}`;
}

function formatQualityLabel(quality) {
  if (!quality) {
    return "판단 대기";
  }
  return quality.should_stop ? "이번 루프 정리" : "다음 루프 가능";
}

function formatScore(quality) {
  if (!quality) {
    return "- / 2";
  }
  return `${quality.score || 0} / 2`;
}

function normalizeSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractKeywords(text) {
  const matches = String(text || "").match(/[\p{L}\p{N}]{2,}/gu) || [];
  const keywords = [];
  const seen = new Set();

  matches.forEach((token) => {
    const normalized = stripKoreanParticle(token.toLowerCase());
    if (!normalized || normalized.length < 2 || STOPWORDS.has(normalized) || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    keywords.push(normalized);
  });

  return keywords.slice(0, 6);
}

function stripKoreanParticle(token) {
  return token.replace(
    /(으로|에서|에게|까지|부터|처럼|보다|조차|마저|이나|나|은|는|이|가|을|를|의|에|와|과|도|만|로|라|야|요)$/u,
    ""
  );
}

function extractKeyPoints(text) {
  const cleaned = String(text || "")
    .replace(/^\[[^\]]+\]\s*/gm, "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !isStructuralFeedbackLine(line));

  if (cleaned.length) {
    return cleaned.slice(0, 5);
  }

  return String(text || "")
    .split(/[.!?]\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function isStructuralFeedbackLine(line) {
  return (
    line.startsWith("판정:") ||
    [
      "설정:",
      "구조:",
      "미래 리스크:",
      "다음 액션:",
      "반응:",
      "몰입:",
      "이탈감:",
    ].some((prefix) => line.startsWith(prefix))
  );
}

function joinKeyPoints(text) {
  const items = extractKeyPoints(text);
  return items.length ? items.join(" / ") : "대기 중";
}

function formatNumber(value) {
  return new Intl.NumberFormat("ko-KR").format(value);
}

function trimText(text, limit) {
  const compact = String(text || "").replace(/\s+/g, " ").trim();
  if (compact.length <= limit) {
    return compact;
  }
  return `${compact.slice(0, limit - 1)}…`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

const POSITIVE_SIGNAL_PATTERNS = [
  "좋",
  "강",
  "선명",
  "탄탄",
  "흥미",
  "몰입",
  "궁금",
  "매력",
  "기대",
  "살아",
  "재밌",
];

const CONCERN_SIGNAL_PATTERNS = [
  "약하",
  "어색",
  "흐리",
  "부족",
  "혼란",
  "헷갈",
  "이탈",
  "끊",
  "늘어",
  "과하",
  "문제",
  "불안",
  "모호",
];

const CANON_POSITIVE_SIGNAL_PATTERNS = ["이상 없음", "안정", "정합", "매끄럽"];
const CANON_CONCERN_SIGNAL_PATTERNS = [
  "다만",
  "주의",
  "보강",
  "보완",
  "점검",
  "조정",
  "정리",
  "눌러",
  "줄여",
  "필요",
];
const ECHO_POSITIVE_SIGNAL_PATTERNS = ["보고 싶", "끌리", "재밌", "재미", "와닿", "궁금"];
const ECHO_CONCERN_SIGNAL_PATTERNS = ["지루", "심심", "안 읽", "거리", "부담", "뜬금"];

const STOPWORDS = new Set([
  "이상",
  "없음",
  "다만",
  "지금",
  "이번",
  "장면",
  "최종본",
  "초안",
  "설정",
  "구조",
  "피드백",
  "댓글",
  "카논",
  "에코",
  "루네",
  "서고",
  "정말",
  "진짜",
  "바로",
  "조금",
  "한번",
  "이야기",
  "문장",
  "느낌",
  "반응",
  "요약",
  "대기",
  "있습니다",
  "없습니다",
  "같아",
  "같습니다",
]);
