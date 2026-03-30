const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const indexHtml = fs.readFileSync(path.join(repoRoot, "frontend", "index.html"), "utf8");
const appSource =
  fs.readFileSync(path.join(repoRoot, "frontend", "app.js"), "utf8") +
  "\n;globalThis.__appTestHooks = { state, els };";

class FakeClassList {
  constructor(initial = []) {
    this.values = new Set(initial.filter(Boolean));
  }

  add(...tokens) {
    tokens.forEach((token) => this.values.add(token));
  }

  remove(...tokens) {
    tokens.forEach((token) => this.values.delete(token));
  }

  toggle(token, force) {
    if (force === undefined) {
      if (this.values.has(token)) {
        this.values.delete(token);
        return false;
      }
      this.values.add(token);
      return true;
    }
    if (force) {
      this.values.add(token);
      return true;
    }
    this.values.delete(token);
    return false;
  }

  contains(token) {
    return this.values.has(token);
  }

  toString() {
    return [...this.values].join(" ");
  }
}

class FakeEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.target = init.target || null;
    this.currentTarget = null;
    this.key = init.key || "";
    this.defaultPrevented = false;
  }

  preventDefault() {
    this.defaultPrevented = true;
  }
}

class FakeElement {
  constructor(document, options = {}) {
    this.ownerDocument = document;
    this.id = options.id || "";
    this.tagName = String(options.tagName || "div").toUpperCase();
    this.dataset = { ...(options.dataset || {}) };
    this.classList = new FakeClassList(options.classNames || []);
    this.listeners = new Map();
    this.style = {};
    this.attributes = { ...(options.attributes || {}) };
    this.textContent = options.textContent || "";
    this.value = options.value || "";
    this.checked = Boolean(options.checked);
    this.disabled = Boolean(options.disabled);
    this._innerHTML = "";
    this.children = [];
    this.parentNode = null;
    this.href = "";
    this.download = "";
    this.clickCount = 0;
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
  }

  addEventListener(type, handler) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(handler);
  }

  dispatchEvent(event) {
    event.target = event.target || this;
    event.currentTarget = this;
    const handlers = this.listeners.get(event.type) || [];
    handlers.forEach((handler) => handler.call(this, event));
    return !event.defaultPrevented;
  }

  click() {
    this.clickCount += 1;
    this.dispatchEvent(new FakeEvent("click", { target: this }));
  }

  focus() {
    this.ownerDocument.activeElement = this;
  }

  closest(selector) {
    if (selector === "button") {
      return this.tagName === "BUTTON" ? this : null;
    }
    return null;
  }

  setAttribute(name, value) {
    const stringValue = String(value);
    this.attributes[name] = stringValue;
    if (name === "id") {
      this.id = stringValue;
    }
    if (name === "class") {
      this.classList = new FakeClassList(stringValue.split(/\s+/));
    }
    if (name.startsWith("data-")) {
      const key = name
        .slice(5)
        .replace(/-([a-z])/g, (_, char) => char.toUpperCase());
      this.dataset[key] = stringValue;
    }
  }

  getAttribute(name) {
    if (name === "class") {
      return this.classList.toString();
    }
    return this.attributes[name] || null;
  }

  append(...children) {
    children.forEach((child) => {
      child.parentNode = this;
      this.children.push(child);
    });
  }

  remove() {
    if (!this.parentNode) {
      return;
    }
    this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
    this.parentNode = null;
  }
}

class FakeDocument {
  constructor(html) {
    this.listeners = new Map();
    this.activeElement = null;
    this.elementsById = new Map();
    this.selectorMap = new Map();
    this.body = this.#buildBody(html);
    this.#buildElements(html);
    this.#buildStaticSelectors(html);
  }

  #buildBody(html) {
    const bodyClassMatch = html.match(/<body[^>]*class="([^"]*)"/i);
    const classNames = bodyClassMatch ? bodyClassMatch[1].split(/\s+/) : [];
    return new FakeElement(this, { tagName: "body", classNames });
  }

  #buildElements(html) {
    const ids = [...html.matchAll(/id="([^"]+)"/g)].map((match) => match[1]);
    ids.forEach((id) => {
      const tagMatch = html.match(new RegExp(`<([a-zA-Z0-9-]+)[^>]*\\bid="${id}"[^>]*>`, "i"));
      const rawTag = tagMatch ? tagMatch[0] : "";
      const tagName = tagMatch ? tagMatch[1] : "div";
      const classMatch = rawTag.match(/\bclass="([^"]*)"/i);
      const classNames = classMatch ? classMatch[1].split(/\s+/) : [];
      const valueMatch = rawTag.match(/\bvalue="([^"]*)"/i);
      const dataset = {};
      for (const match of rawTag.matchAll(/\bdata-([a-z0-9-]+)="([^"]*)"/gi)) {
        const key = match[1].replace(/-([a-z])/g, (_, char) => char.toUpperCase());
        dataset[key] = match[2];
      }
      const element = new FakeElement(this, {
        id,
        tagName,
        classNames,
        dataset,
        value: valueMatch ? valueMatch[1] : "",
        checked: /\bchecked\b/i.test(rawTag),
        disabled: /\bdisabled\b/i.test(rawTag),
      });
      this.elementsById.set(id, element);
    });
  }

  #buildStaticSelectors(html) {
    const panels = [...html.matchAll(/<([a-zA-Z0-9-]+)[^>]*data-view-panel="([^"]+)"[^>]*>/gi)].map(
      (match) => {
        const rawTag = match[0];
        const classMatch = rawTag.match(/\bclass="([^"]*)"/i);
        const classNames = classMatch ? classMatch[1].split(/\s+/) : [];
        return new FakeElement(this, {
          tagName: match[1],
          classNames,
          dataset: { viewPanel: match[2] },
        });
      }
    );

    this.selectorMap.set("[data-view-panel]", panels);
    this.selectorMap.set("[data-history-file]", []);
    this.selectorMap.set("[data-iteration]", []);
    this.selectorMap.set("[data-attachment-index]", []);
  }

  getElementById(id) {
    return this.elementsById.get(id) || null;
  }

  addEventListener(type, handler) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(handler);
  }

  dispatchEvent(event) {
    const handlers = this.listeners.get(event.type) || [];
    handlers.forEach((handler) => handler.call(this, event));
  }

  querySelectorAll(selector) {
    return [...(this.selectorMap.get(selector) || [])];
  }

  createElement(tagName) {
    return new FakeElement(this, { tagName });
  }
}

function jsonClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function buildStatePayload() {
  return {
    greeting: "Archive online.",
    settings: {
      base: "Base rules",
      spoiler: "Spoiler notes",
      style: "Noir cadence",
    },
    loop_state: {
      status: "idle",
      stage: "idle",
      message: "Awaiting plot input.",
      run_id: null,
      title: "Stored Session",
      plot: "Stored plot from the last archive session.",
      current_iteration: 1,
      config: {
        max_loops: 3,
        early_stop_enabled: true,
        parallel_feedback: true,
      },
      cards: [
        { loop_index: 1, status: "done" },
        { loop_index: 2, status: "skipped" },
        { loop_index: 3, status: "skipped" },
      ],
      iterations: [
        {
          loop_index: 1,
          status: "done",
          draft: "Draft copy",
          feedback: "Feedback copy",
          comment: "Comment copy",
          final: "Final copy",
          draft_summary: "Draft summary",
          feedback_summary: "Feedback summary",
          comment_summary: "Comment summary",
          final_summary: "Final summary",
          feedback_structured: {
            verdict: "ok",
            verdict_label: "이상 없음",
            sections: {
              setting: ["없음"],
              structure: ["초반 구조가 안정적으로 들어옵니다."],
              future_risk: ["없음"],
              next_action: ["현재 구조를 유지한 채 최종본으로 정리해도 괜찮습니다."],
            },
          },
          comment_structured: {
            sections: {
              reaction: ["분위기가 바로 잡힙니다."],
              immersion: ["첫 장면에서 바로 끌립니다."],
              dropoff: ["중간 연결 문장 하나가 조금 늘어집니다."],
            },
          },
          quality: {
            should_stop: true,
            score: 2,
            reasons: ["Locked in."],
          },
          history_file: "stored-session-loop01.json",
        },
      ],
      usage_summary: {
        total_tokens: 2200,
        total_cost_usd: 0.0345,
      },
      last_quality: null,
      active_persona: null,
    },
    sil_log: [
      {
        timestamp: "2026-03-30T08:00:00Z",
        kind: "loop",
        display: "Idle archive heartbeat.",
      },
    ],
    history: [
      {
        filename: "alpha.json",
        title: "Alpha Archive",
        plot: "The first plot thread",
        created_at: "2026-03-28T11:00:00Z",
        loop_index: 1,
        outputs: {
          draft: "Alpha draft",
          feedback: "Alpha canon note",
          comment: "Alpha echo note",
          final: "Alpha final passage",
        },
        comment_structured: {
          sections: {
            reaction: ["첫 반응이 선명합니다."],
            immersion: ["계속 읽고 싶습니다."],
            dropoff: ["없음"],
          },
        },
        quality: {
          should_stop: false,
          score: 1,
          reasons: ["Needs one more pass."],
        },
        usage_summary: {
          total_tokens: 800,
          total_cost_usd: 0.0123,
        },
        prompts: {},
      },
      {
        filename: "beta.json",
        title: "Beta Mystery",
        plot: "A mystery under the archive lamps",
        created_at: "2026-03-29T09:30:00Z",
        loop_index: 2,
        outputs: {
          draft: "Beta draft",
          feedback: "Beta canon note",
          comment: "Beta echo note",
          final: "Beta final passage",
        },
        comment_structured: {
          sections: {
            reaction: ["긴장감이 또렷합니다."],
            immersion: ["다음 장면이 바로 궁금해집니다."],
            dropoff: ["중반 설명이 한 번 길어집니다."],
          },
        },
        quality: {
          should_stop: true,
          score: 2,
          reasons: ["Resolved cleanly."],
        },
        usage_summary: {
          total_tokens: 1200,
          total_cost_usd: 0.0234,
        },
        prompts: {},
      },
    ],
    meta: {
      last_return_days: 3,
      total_completed_loops: 12,
      affinity_stage: "warm",
    },
    service: {
      mode: "mock",
      model: "gemini-2.5-pro",
    },
  };
}

function buildEstimateResponse() {
  return {
    loop_config: {
      max_loops: 2,
    },
    total: {
      total_tokens: 2400,
      prompt_tokens: 0,
      estimated_output_tokens: 0,
      estimated_cost_usd: 0.1234,
      approximate: true,
    },
    tokens_per_call: [
      {
        persona: "rune_draft",
        prompt_tokens: 300,
        estimated_output_tokens: 500,
        estimated_cost_usd: 0.025,
        mode: "heuristic",
      },
      {
        persona: "canon_review",
        prompt_tokens: 150,
        estimated_output_tokens: 200,
        estimated_cost_usd: 0.015,
        mode: "heuristic",
      },
      {
        persona: "echo_comment",
        prompt_tokens: 150,
        estimated_output_tokens: 200,
        estimated_cost_usd: 0.0134,
        mode: "heuristic",
      },
      {
        persona: "rune_final",
        prompt_tokens: 350,
        estimated_output_tokens: 550,
        estimated_cost_usd: 0.07,
        mode: "heuristic",
      },
    ],
  };
}

function buildRunningLoopState(payload) {
  return {
    status: "running",
    stage: "rune_draft",
    message: "Run started.",
    run_id: "run-42",
    title: payload.title,
    plot: payload.plot,
    current_iteration: 1,
    config: payload.loop_config,
    cards: [
      { loop_index: 1, status: "active" },
      { loop_index: 2, status: "pending" },
    ],
    iterations: [],
    usage_summary: {
      total_tokens: 0,
      total_cost_usd: 0,
    },
    last_quality: null,
    active_persona: "rune",
  };
}

function buildCancelledLoopState(payload) {
  return {
    status: "cancelled",
    stage: "cancelled",
    message: "Run cancelled.",
    run_id: "run-42",
    title: payload.title,
    plot: payload.plot,
    current_iteration: 1,
    config: payload.loop_config,
    cards: [
      { loop_index: 1, status: "cancelled" },
      { loop_index: 2, status: "skipped" },
    ],
    iterations: [],
    usage_summary: {
      total_tokens: 0,
      total_cost_usd: 0,
    },
    last_quality: null,
    active_persona: null,
  };
}

async function flushAsyncWork(rounds = 4) {
  for (let index = 0; index < rounds; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

function createHarness() {
  const document = new FakeDocument(indexHtml);
  const fetchCalls = [];
  const statePayload = buildStatePayload();
  const estimateResponse = buildEstimateResponse();
  let serverLoopState = jsonClone(statePayload.loop_state);
  let serverHistory = jsonClone(statePayload.history);
  let serverSilLog = jsonClone(statePayload.sil_log);
  let lastRunPayload = null;
  let intervalId = 0;
  const intervalHandlers = new Map();
  const windowListeners = new Map();

  async function fetchStub(resource, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const body = options.body ? JSON.parse(options.body) : null;
    fetchCalls.push({ resource, method, body });

    if (resource === "/api/state" && method === "GET") {
      return buildResponse({
        ...jsonClone(statePayload),
        loop_state: jsonClone(serverLoopState),
        history: jsonClone(serverHistory),
        sil_log: jsonClone(serverSilLog),
      });
    }

    if (resource === "/api/settings" && method === "PUT") {
      statePayload.settings = jsonClone(body.settings);
      return buildResponse({ settings: jsonClone(body.settings) });
    }

    if (resource === "/api/cost-estimate" && method === "POST") {
      return buildResponse(jsonClone(estimateResponse));
    }

    if (resource === "/api/run" && method === "POST") {
      lastRunPayload = jsonClone(body);
      serverLoopState = buildRunningLoopState(lastRunPayload);
      return buildResponse({
        run_id: serverLoopState.run_id,
        loop_state: jsonClone(serverLoopState),
      });
    }

    if (resource === "/api/run/cancel" && method === "POST") {
      serverLoopState = buildCancelledLoopState(lastRunPayload || body || {
        title: "",
        plot: "",
        loop_config: {
          max_loops: 3,
          early_stop_enabled: true,
          parallel_feedback: true,
        },
      });
      return buildResponse({ loop_state: jsonClone(serverLoopState) });
    }

    if (resource === "/api/loop-state" && method === "GET") {
      return buildResponse(jsonClone(serverLoopState));
    }

    if (resource === "/api/history" && method === "GET") {
      return buildResponse(jsonClone(serverHistory));
    }

    if (resource === "/api/sil-log" && method === "GET") {
      return buildResponse(jsonClone(serverSilLog));
    }

    return {
      ok: false,
      async json() {
        return { detail: `Unhandled request: ${method} ${resource}` };
      },
    };
  }

  const windowObject = {
    document,
    requestAnimationFrame(callback) {
      callback();
      return 1;
    },
    setTimeout(callback) {
      callback();
      return 1;
    },
    clearTimeout() {},
    setInterval(callback) {
      intervalId += 1;
      intervalHandlers.set(intervalId, callback);
      return intervalId;
    },
    clearInterval(id) {
      intervalHandlers.delete(id);
    },
    addEventListener(type, handler) {
      if (!windowListeners.has(type)) {
        windowListeners.set(type, []);
      }
      windowListeners.get(type).push(handler);
    },
    dispatchEvent(event) {
      const handlers = windowListeners.get(event.type) || [];
      handlers.forEach((handler) => handler.call(windowObject, event));
    },
    URL: {
      createObjectURL() {
        return "blob://fake";
      },
      revokeObjectURL() {},
    },
  };

  const context = {
    console,
    document,
    window: windowObject,
    fetch: fetchStub,
    setTimeout: windowObject.setTimeout,
    clearTimeout: windowObject.clearTimeout,
    setInterval: windowObject.setInterval,
    clearInterval: windowObject.clearInterval,
    Blob,
    URL: windowObject.URL,
    Intl,
    Promise,
    Math,
    Number,
    String,
    Boolean,
    Array,
    Object,
    Date,
    JSON,
    RegExp,
    HTMLElement: FakeElement,
    Event: FakeEvent,
    KeyboardEvent: FakeEvent,
    navigator: { userAgent: "node-test" },
    globalThis: null,
  };
  context.globalThis = context;

  vm.runInNewContext(appSource, context, {
    filename: "frontend/app.js",
  });

  return {
    context,
    document,
    fetchCalls,
    get hooks() {
      return context.__appTestHooks;
    },
  };
}

function buildResponse(payload) {
  return {
    ok: true,
    async json() {
      return jsonClone(payload);
    },
  };
}

async function trigger(element, type, init = {}) {
  element.dispatchEvent(new FakeEvent(type, { target: element, ...init }));
  await flushAsyncWork();
}

async function run() {
  const harness = createHarness();
  const { document, fetchCalls } = harness;
  const { state, els } = harness.hooks;

  document.dispatchEvent(new FakeEvent("DOMContentLoaded", { target: document }));
  await flushAsyncWork();

  assert.equal(fetchCalls[0].resource, "/api/state");
  assert.equal(els.serviceMode.textContent, "mock");
  assert.equal(els.serviceModel.textContent, "gemini-2.5-pro");
  assert.equal(els.titleStartButton.disabled, false);
  assert.equal(state.currentView, "main");
  assert.match(els.chatThread.innerHTML, /message-meta-row/);
  assert.match(els.chatThread.innerHTML, /loop 1/i);
  assert.match(els.iterationFocus.innerHTML, /structured-feedback/);
  assert.match(els.iterationFocus.innerHTML, /이탈감/);

  els.titleStartButton.click();
  await flushAsyncWork();
  assert.equal(document.body.classList.contains("title-active"), false);
  assert.equal(document.body.classList.contains("title-dismissed"), true);
  assert.equal(els.titleScreen.getAttribute("aria-hidden"), "true");
  assert.equal(document.activeElement, els.plotInput);

  els.viewButtonWorkroom.click();
  await flushAsyncWork();
  assert.equal(state.currentView, "workroom");
  assert.equal(els.viewButtonWorkroom.classList.contains("selected"), true);
  const panels = document.querySelectorAll("[data-view-panel]");
  assert.equal(panels.find((panel) => panel.dataset.viewPanel === "workroom").classList.contains("active"), true);
  assert.equal(panels.find((panel) => panel.dataset.viewPanel === "main").classList.contains("active"), false);

  els.settingsBase.value = "Updated base";
  els.settingsSpoiler.value = "Updated spoiler";
  els.settingsStyle.value = "Updated style";
  els.saveSettingsButton.click();
  await flushAsyncWork();
  const saveCall = fetchCalls.find(
    (entry) => entry.resource === "/api/settings" && entry.method === "PUT"
  );
  assert.deepEqual(saveCall.body, {
    settings: {
      base: "Updated base",
      spoiler: "Updated spoiler",
      style: "Updated style",
    },
  });

  els.titleInput.value = "Archive Run";
  els.plotInput.value = "A lantern flickers under the archive door.";
  els.maxLoopsInput.value = "2";
  els.contextModeInput.value = "hybrid";
  els.earlyStopInput.checked = true;
  els.parallelInput.checked = true;
  els.estimateButton.click();
  await flushAsyncWork();
  const estimateCall = fetchCalls.find(
    (entry) => entry.resource === "/api/cost-estimate" && entry.method === "POST"
  );
  assert.equal(estimateCall.body.title, "Archive Run");
  assert.equal(estimateCall.body.plot, "A lantern flickers under the archive door.");
  assert.equal(estimateCall.body.loop_config.max_loops, 2);
  assert.match(els.estimateSummary.innerHTML, /2,400/);
  assert.match(els.estimateSummary.innerHTML, /\$0\.1234/);

  els.historySearchInput.value = "beta";
  await trigger(els.historySearchInput, "input");
  assert.match(els.historyList.innerHTML, /Beta Mystery/);
  assert.doesNotMatch(els.historyList.innerHTML, /Alpha Archive/);

  els.historySearchInput.value = "";
  await trigger(els.historySearchInput, "input");
  els.historyFilterInput.value = "continue";
  await trigger(els.historyFilterInput, "change");
  assert.match(els.historyList.innerHTML, /Alpha Archive/);
  assert.doesNotMatch(els.historyList.innerHTML, /Beta Mystery/);

  els.runButton.click();
  await flushAsyncWork();
  const runCall = fetchCalls.find(
    (entry) => entry.resource === "/api/run" && entry.method === "POST"
  );
  assert.equal(runCall.body.title, "Archive Run");
  assert.equal(state.currentView, "main");
  assert.equal(els.runButton.disabled, true);
  assert.equal(els.cancelButton.disabled, false);
  assert.equal(els.loopStageText.textContent, "rune_draft");

  els.cancelButton.click();
  await flushAsyncWork();
  const cancelCall = fetchCalls.find(
    (entry) => entry.resource === "/api/run/cancel" && entry.method === "POST"
  );
  assert.ok(cancelCall);
  assert.equal(els.runButton.disabled, false);
  assert.equal(els.cancelButton.disabled, true);
  assert.equal(els.loopStageText.textContent, "cancelled");

  console.log("frontend interaction smoke runner passed");
}

run().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
