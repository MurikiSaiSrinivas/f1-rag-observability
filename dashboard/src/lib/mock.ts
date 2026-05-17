/**
 * Mock fixtures matching src/lib/types.ts. Foundation-stage stand-in for the
 * FastAPI backend. Representative, not exhaustive — enough to drive the UI and
 * prove the typed contract holds end to end.
 */
import type {
  AdminOverview,
  AnswerView,
  AskResult,
  Flag,
  GuardrailTriggered,
  HistoryItem,
  ProvenanceSource,
  RequestChunk,
  Route,
  Score,
  Span,
  TraceDetail,
  TraceRow,
} from "@/lib/types";

export const MOCK_TRACES: TraceRow[] = [
  {
    request_id: "req_8f3a2c",
    created_at: "2026-05-17T09:14:22Z",
    client_id: "cl_a91f",
    question: "Who is Lando Norris?",
    route: "narrative",
    latency_ms: 1240,
    total_tokens: 1820,
    total_cost_usd: 0.0008,
    faithfulness: 0.92,
    feedback: "up",
    final_status: "success",
    flags: [],
  },
  {
    request_id: "req_b1d09e",
    created_at: "2026-05-17T09:31:08Z",
    client_id: "cl_a91f",
    question: "How many wins did Verstappen have in 2023?",
    route: "structured",
    latency_ms: 860,
    total_tokens: 640,
    total_cost_usd: 0.0004,
    faithfulness: null,
    feedback: null,
    final_status: "success",
    flags: [],
  },
  {
    request_id: "req_4c77a1",
    created_at: "2026-05-17T10:02:51Z",
    client_id: "cl_77b3",
    question:
      "What happened at the 2021 Abu Dhabi GP and how did the title end?",
    route: "both",
    latency_ms: 3910,
    total_tokens: 4120,
    total_cost_usd: 0.0021,
    faithfulness: 0.78,
    feedback: "down",
    final_status: "flagged",
    flags: ["hallucination"],
  },
];

export const MOCK_OVERVIEW: AdminOverview = {
  kpis: {
    total_requests: 1287,
    error_rate: 0.031,
    avg_latency_ms: 1980,
    cost_today_usd: 0.42,
    avg_faithfulness: 0.86,
    feedback_ratio: 0.74,
  },
  requests_over_time: [
    { t: "09:00", requests: 42, errors: 1 },
    { t: "10:00", requests: 61, errors: 2 },
    { t: "11:00", requests: 58, errors: 0 },
    { t: "12:00", requests: 73, errors: 3 },
  ],
  route_distribution: [
    { route: "narrative", count: 612 },
    { route: "structured", count: 431 },
    { route: "both", count: 244 },
  ],
  top_flags: [
    { flag_name: "hallucination", count: 18 },
    { flag_name: "sql_zero_results", count: 11 },
    { flag_name: "route_misclassified", count: 7 },
  ],
  recent: MOCK_TRACES,
};

export const MOCK_HISTORY: HistoryItem[] = MOCK_TRACES.map((t) => ({
  request_id: t.request_id,
  question: t.question,
  route: t.route,
  created_at: t.created_at,
  feedback: t.feedback,
  flagged: t.flags.length > 0,
}));

// --- trace detail builder ---------------------------------------------------

let _sid = 0;
function sp(
  requestId: string,
  parent: string | null,
  name: string,
  span_type: Span["span_type"],
  start: number,
  end: number,
  attributes: Record<string, unknown> = {},
  status: Span["status"] = "ok",
): Span {
  return {
    span_id: `sp_${++_sid}`,
    request_id: requestId,
    parent_span_id: parent,
    name,
    span_type,
    start_ts: start,
    end_ts: end,
    duration_ms: end - start,
    status,
    attributes,
  };
}

function buildSpans(
  id: string,
  route: Route,
  total: number,
): Span[] {
  _sid = 0;
  const root = "sp_1";
  const out: Span[] = [
    sp(id, null, "ask", "orchestration", 0, total, {
      route,
      prompt_version: "v1",
    }),
  ];
  out.push(
    sp(id, root, "guardrails.input", "guardrail", 0, 26, {
      rules_checked: ["off_topic", "prompt_injection", "pii_in_question", "too_long"],
      triggered: [],
      action: "pass",
    }),
  );
  out.push(
    sp(id, root, "router.classify", "llm", 26, 232, {
      model: "gpt-4o-mini",
      category: route,
      confidence: route === "both" ? 0.74 : 0.94,
      tokens: 181,
      cost_usd: 0.00004,
    }),
  );

  if (route === "narrative" || route === "both") {
    const ragStart = 232;
    const ragEnd = route === "both" ? 1900 : total - 30;
    const ragId = `sp_${_sid + 1}`;
    out.push(
      sp(id, root, "rag.pipeline", "orchestration", ragStart, ragEnd, {}),
    );
    out.push(
      sp(id, ragId, "rag.embed_query", "retrieval", ragStart, ragStart + 118, {
        model: "text-embedding-3-small",
        embedding_tokens: 14,
      }),
    );
    out.push(
      sp(
        id,
        ragId,
        "rag.vector_search",
        "retrieval",
        ragStart + 118,
        ragStart + 270,
        {
          top_k: 5,
          returned_chunk_ids: 5,
          best_similarity: 0.71,
        },
      ),
    );
    out.push(
      sp(
        id,
        ragId,
        "guardrails.retrieval",
        "guardrail",
        ragStart + 270,
        ragStart + 280,
        {
          triggered: route === "both" ? ["low_similarity"] : [],
          action: route === "both" ? "warn" : "pass",
        },
        route === "both" ? "error" : "ok",
      ),
    );
    out.push(
      sp(id, ragId, "rag.synthesis", "llm", ragStart + 280, ragEnd, {
        model: "gpt-4o-mini",
        prompt_tokens: 2140,
        completion_tokens: 320,
        cost_usd: 0.00071,
        used_chunk_ids: 3,
      }),
    );
  }

  if (route === "structured" || route === "both") {
    const sqlStart = route === "both" ? 1900 : 232;
    const sqlEnd = route === "both" ? 2600 : total - 130;
    const sqlId = `sp_${_sid + 1}`;
    out.push(
      sp(id, root, "sql.pipeline", "orchestration", sqlStart, sqlEnd, {}),
    );
    out.push(
      sp(id, sqlId, "sql.generate", "llm", sqlStart, sqlEnd - 120, {
        model: "gpt-4o-mini",
        tokens: 410,
        cost_usd: 0.00012,
      }),
    );
    out.push(
      sp(id, sqlId, "sql.execute", "sql", sqlEnd - 120, sqlEnd, {
        row_count: route === "both" ? 1 : 1,
        execution_ms: 120,
        timed_out: false,
      }),
    );
  }

  const mergeStart = route === "both" ? 2600 : route === "structured" ? total - 130 : total - 30;
  const mergeEnd = total - 16;
  out.push(
    sp(
      id,
      root,
      "merger.merge",
      route === "narrative" ? "orchestration" : "llm",
      mergeStart,
      mergeEnd,
      {
        route,
        llm_called: route !== "narrative",
        ...(route !== "narrative"
          ? { model: "gpt-4o-mini", tokens: 980, cost_usd: 0.0014 }
          : {}),
      },
    ),
  );
  out.push(
    sp(id, root, "guardrails.output", "guardrail", mergeEnd, total, {
      triggered: route === "both" ? ["hallucination"] : [],
      action: route === "both" ? "warn" : "pass",
    }),
  );
  return out;
}

const CHUNKS: (RequestChunk & {
  title: string;
  source: "wikipedia" | "fia";
})[] = [
  {
    request_id: "",
    chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0007",
    rank: 1,
    similarity: 0.71,
    used_in_prompt: true,
    title: "2021 Abu Dhabi Grand Prix",
    source: "wikipedia",
  },
  {
    request_id: "",
    chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0008",
    rank: 2,
    similarity: 0.68,
    used_in_prompt: true,
    title: "2021 Abu Dhabi Grand Prix",
    source: "wikipedia",
  },
  {
    request_id: "",
    chunk_id: "wikipedia/people/max_verstappen#0021",
    rank: 3,
    similarity: 0.55,
    used_in_prompt: true,
    title: "Max Verstappen",
    source: "wikipedia",
  },
  {
    request_id: "",
    chunk_id: "fia/2021/sporting_regulations#p048-02",
    rank: 4,
    similarity: 0.41,
    used_in_prompt: false,
    title: "2021 FIA Formula One Sporting Regulations",
    source: "fia",
  },
  {
    request_id: "",
    chunk_id: "wikipedia/seasons/2021_formula_one#0033",
    rank: 5,
    similarity: 0.38,
    used_in_prompt: false,
    title: "2021 Formula One World Championship",
    source: "wikipedia",
  },
];

export function mockTraceDetail(requestId: string): TraceDetail {
  const row =
    MOCK_TRACES.find((t) => t.request_id === requestId) ?? MOCK_TRACES[0];
  const route = row.route;
  const hasRag = route === "narrative" || route === "both";
  const hasSql = route === "structured" || route === "both";

  const scores: Score[] = hasRag
    ? (
        [
          ["faithfulness", row.faithfulness ?? 0.85],
          ["answer_relevancy", 0.9],
          ["context_relevancy", 0.7],
        ] as const
      ).map(([metric, value]) => ({
        request_id: requestId,
        metric,
        value,
        scored_at: row.created_at,
        scorer_model: "gpt-4o-mini",
      }))
    : [];

  const guardrails: GuardrailTriggered[] =
    route === "both"
      ? [
          {
            id: "gr_1",
            request_id: requestId,
            rule_name: "low_similarity",
            stage: "retrieval",
            implementation: "hand_rolled",
            action: "warn",
            severity: "warning",
            reason:
              "Top retrieval similarity 0.71 with 2 of 5 chunks below the 0.5 threshold — sources may be weak.",
            triggered_at: row.created_at,
          },
          {
            id: "gr_2",
            request_id: requestId,
            rule_name: "hallucination",
            stage: "output",
            implementation: "hand_rolled",
            action: "warn",
            severity: "critical",
            reason:
              "RAGAS faithfulness 0.78 < 0.85 target; answer asserts a detail not grounded in retrieved context.",
            triggered_at: row.created_at,
          },
        ]
      : [];

  const flags: Flag[] =
    route === "both"
      ? [
          {
            id: "fl_1",
            request_id: requestId,
            flag_name: "hallucination",
            description:
              "Answer contains a claim not supported by any retrieved chunk.",
            severity: "critical",
            flagged_at: row.created_at,
          },
        ]
      : [];

  return {
    request: {
      request_id: requestId,
      client_id: row.client_id,
      session_id: "ses_0007",
      question: row.question,
      final_answer:
        route === "structured"
          ? "Max Verstappen won 19 races in the 2023 season."
          : "On the final lap of the 2021 Abu Dhabi Grand Prix, Max Verstappen passed Lewis Hamilton to win the race and the World Championship, after a contentious safety-car restart.",
      route,
      model: "gpt-4o-mini",
      prompt_version: "v1",
      temperature: 0.2,
      prompt_tokens: hasRag ? 2140 : 410,
      completion_tokens: 320,
      embedding_tokens: hasRag ? 14 : 0,
      total_cost_usd: row.total_cost_usd,
      latency_ms: row.latency_ms,
      final_status: row.final_status,
      created_at: row.created_at,
      replay_of_request_id: null,
    },
    route_decision: {
      request_id: requestId,
      category: route,
      confidence: route === "both" ? 0.74 : 0.94,
      reasoning:
        route === "both"
          ? "Question asks for a narrative ('what happened') and an outcome that needs the standings table — needs both paths."
          : route === "structured"
            ? "Pure aggregation over race results — count of wins. SQL path."
            : "Explanatory/biographical question with no aggregation — vector RAG path.",
      router_model: "gpt-4o-mini",
      router_tokens: 181,
      router_latency_ms: 206,
    },
    spans: buildSpans(requestId, route, row.latency_ms),
    request_chunks: hasRag
      ? CHUNKS.map((c) => ({ ...c, request_id: requestId }))
      : [],
    sql_execution: hasSql
      ? {
          request_id: requestId,
          generated_sql:
            "SELECT d.full_name, ds.wins\nFROM driver_standings ds\nJOIN drivers d ON d.driver_id = ds.driver_id\nWHERE ds.season = 2023 AND d.driver_id = 'max_verstappen';",
          cleaned_sql:
            "SELECT d.full_name, ds.wins FROM driver_standings ds JOIN drivers d ON d.driver_id = ds.driver_id WHERE ds.season = 2023 AND d.driver_id = 'max_verstappen';",
          row_count: 1,
          execution_ms: 120,
          timed_out: false,
          error: null,
          result_rows: [{ full_name: "Max Verstappen", wins: 19 }],
          gen_model: "gpt-4o-mini",
          gen_tokens: 410,
          gen_latency_ms: route === "both" ? 580 : 450,
        }
      : null,
    scores,
    guardrails,
    flags,
    feedback:
      row.feedback === null
        ? null
        : {
            id: "fb_1",
            request_id: requestId,
            thumbs: row.feedback,
            comment:
              row.feedback === "down"
                ? "The race summary mixed up a couple of the lap details."
                : null,
            submitted_at: row.created_at,
          },
  };
}

// --- public answer + provenance --------------------------------------------

/** Build document text + accurate highlight offsets for the used passages. */
function buildDoc(
  parts: (string | { h: string; chunk_id: string })[],
): Pick<ProvenanceSource, "document_text" | "highlights"> {
  let text = "";
  const highlights: ProvenanceSource["highlights"] = [];
  for (const p of parts) {
    if (typeof p === "string") {
      text += p;
    } else {
      const start = text.length;
      text += p.h;
      highlights.push({ start, end: text.length, chunk_id: p.chunk_id });
    }
  }
  return { document_text: text, highlights };
}

const LANDO_DOC: ProvenanceSource = {
  kind: "wikipedia",
  title: "Lando Norris",
  url: "https://en.wikipedia.org/wiki/Lando_Norris",
  page_number: null,
  ...buildDoc([
    "Lando Norris is a British racing driver currently competing in Formula One for McLaren. ",
    {
      h: "Born on 13 November 1999 in Bristol, England, Norris won the 2017 FIA Formula 3 European Championship and finished runner-up in the 2018 FIA Formula 2 Championship before graduating to Formula One.",
      chunk_id: "wikipedia/people/lando_norris#0003",
    },
    " He made his Formula One debut with McLaren in 2019. ",
    {
      h: "Norris took his maiden Formula One victory at the 2024 Miami Grand Prix, his 110th start, and has since established himself as a consistent front-runner and a title contender.",
      chunk_id: "wikipedia/people/lando_norris#0011",
    },
    " Known for his media presence and esports involvement, he founded the Quadrant content and esports group in 2020. He is widely regarded as one of the most marketable drivers of his generation.",
  ]),
};

const ABU_DHABI_DOC: ProvenanceSource = {
  kind: "wikipedia",
  title: "2021 Abu Dhabi Grand Prix",
  url: "https://en.wikipedia.org/wiki/2021_Abu_Dhabi_Grand_Prix",
  page_number: null,
  ...buildDoc([
    "The 2021 Abu Dhabi Grand Prix was the twenty-second and final round of the 2021 Formula One World Championship, held at the Yas Marina Circuit. ",
    {
      h: "Lewis Hamilton led for most of the race, but a late safety car — deployed after Nicholas Latifi's crash — bunched the field together.",
      chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0007",
    },
    " ",
    {
      h: "On the final lap, Max Verstappen, on fresh soft tyres, overtook Hamilton to win the race and clinch his first World Drivers' Championship.",
      chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0008",
    },
    " The race was the subject of significant controversy over the race director's application of the safety car regulations, and the FIA later announced a review of the incident.",
  ]),
};

const GENERIC_DOC: ProvenanceSource = {
  kind: "wikipedia",
  title: "Formula One",
  url: "https://en.wikipedia.org/wiki/Formula_One",
  page_number: null,
  ...buildDoc([
    "Formula One is the highest class of international racing for open-wheel single-seater formula racing cars. ",
    {
      h: "The series is sanctioned by the Fédération Internationale de l'Automobile (FIA) and has been the premier form of motorsport since its inception in 1950.",
      chunk_id: "wikipedia/seasons/formula_one#0001",
    },
    " A Formula One season consists of a series of races, known as Grands Prix, held worldwide.",
  ]),
};

const SQL_2023_WINS = {
  query:
    "SELECT d.full_name, ds.wins\nFROM driver_standings ds\nJOIN drivers d ON d.driver_id = ds.driver_id\nWHERE ds.season = 2023 AND d.driver_id = 'max_verstappen';",
  rows: [{ full_name: "Max Verstappen", wins: 19 }],
  row_count: 1,
};

const RETRIEVED_NARRATIVE = [
  {
    chunk_id: "wikipedia/people/lando_norris#0003",
    rank: 1,
    similarity: 0.81,
    used_in_prompt: true,
    title: "Lando Norris",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "wikipedia/people/lando_norris#0011",
    rank: 2,
    similarity: 0.76,
    used_in_prompt: true,
    title: "Lando Norris",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "wikipedia/people/lando_norris#0002",
    rank: 3,
    similarity: 0.52,
    used_in_prompt: true,
    title: "Lando Norris",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "wikipedia/teams/mclaren#0044",
    rank: 4,
    similarity: 0.39,
    used_in_prompt: false,
    title: "McLaren",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "fia/2024/sporting_regulations#p012-03",
    rank: 5,
    similarity: 0.31,
    used_in_prompt: false,
    title: "2024 FIA Formula One Sporting Regulations",
    source: "fia" as const,
  },
];

const RETRIEVED_BOTH = [
  {
    chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0007",
    rank: 1,
    similarity: 0.71,
    used_in_prompt: true,
    title: "2021 Abu Dhabi Grand Prix",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "wikipedia/races/2021_abu_dhabi_grand_prix#0008",
    rank: 2,
    similarity: 0.68,
    used_in_prompt: true,
    title: "2021 Abu Dhabi Grand Prix",
    source: "wikipedia" as const,
  },
  {
    chunk_id: "wikipedia/seasons/2021_formula_one#0033",
    rank: 3,
    similarity: 0.43,
    used_in_prompt: false,
    title: "2021 Formula One World Championship",
    source: "wikipedia" as const,
  },
];

const GUARDRAILS_BOTH: GuardrailTriggered[] = [
  {
    id: "gr_1",
    request_id: "req_4c77a1",
    rule_name: "low_similarity",
    stage: "retrieval",
    implementation: "hand_rolled",
    action: "warn",
    severity: "warning",
    reason:
      "Top retrieval similarity 0.71 with 1 of 3 chunks below the 0.5 threshold — sources may be weak.",
    triggered_at: "2026-05-17T10:02:51Z",
  },
  {
    id: "gr_2",
    request_id: "req_4c77a1",
    rule_name: "hallucination",
    stage: "output",
    implementation: "hand_rolled",
    action: "warn",
    severity: "critical",
    reason:
      "RAGAS faithfulness 0.78 is below the 0.85 target; the answer asserts a detail not grounded in retrieved context.",
    triggered_at: "2026-05-17T10:02:51Z",
  },
];

export function mockAnswerView(requestId: string): AnswerView {
  if (requestId === "req_b1d09e") {
    return {
      request_id: requestId,
      question: "How many wins did Verstappen have in 2023?",
      route: "structured",
      answer:
        "Max Verstappen won 19 races during the 2023 Formula One season — a single-season record.",
      status: "success",
      retrieved: [],
      source: null,
      sql: SQL_2023_WINS,
      guardrails: [],
      feedback: null,
    };
  }
  if (requestId === "req_4c77a1") {
    return {
      request_id: requestId,
      question:
        "What happened at the 2021 Abu Dhabi GP and how did the title end?",
      route: "both",
      answer:
        "At the 2021 Abu Dhabi Grand Prix, Lewis Hamilton led until a late safety car for Nicholas Latifi's crash. On the final lap Max Verstappen passed Hamilton on fresh tyres to win the race and his first World Championship, ending the season 2023–2022 — a contentious finish that the FIA later reviewed.",
      status: "flagged",
      retrieved: RETRIEVED_BOTH,
      source: ABU_DHABI_DOC,
      sql: {
        query:
          "SELECT driver_id, points FROM driver_standings\nWHERE season = 2021 AND round = 22 ORDER BY position LIMIT 2;",
        rows: [
          { driver_id: "max_verstappen", points: 395.5 },
          { driver_id: "lewis_hamilton", points: 387.5 },
        ],
        row_count: 2,
      },
      guardrails: GUARDRAILS_BOTH,
      feedback: "down",
    };
  }
  if (requestId === "req_8f3a2c") {
    return {
      request_id: requestId,
      question: "Who is Lando Norris?",
      route: "narrative",
      answer:
        "Lando Norris is a British Formula One driver for McLaren. Born in 1999, he won the 2017 FIA Formula 3 European Championship, was F2 runner-up in 2018, and debuted in Formula One with McLaren in 2019. He took his maiden Grand Prix victory at the 2024 Miami Grand Prix and is now a regular title contender.",
      status: "success",
      retrieved: RETRIEVED_NARRATIVE,
      source: LANDO_DOC,
      sql: null,
      guardrails: [],
      feedback: "up",
    };
  }
  // unknown / arbitrary question → generic narrative answer
  return {
    request_id: requestId,
    question: "Tell me about Formula One",
    route: "narrative",
    answer:
      "Formula One is the highest class of international single-seater open-wheel motor racing, sanctioned by the FIA and contested since 1950 across a worldwide series of Grands Prix.",
    status: "success",
    retrieved: [
      {
        chunk_id: "wikipedia/seasons/formula_one#0001",
        rank: 1,
        similarity: 0.66,
        used_in_prompt: true,
        title: "Formula One",
        source: "wikipedia",
      },
    ],
    source: GENERIC_DOC,
    sql: null,
    guardrails: [],
    feedback: null,
  };
}

export function askMock(question: string): AskResult {
  const q = question.toLowerCase();
  if (q.includes("lando") || q.includes("norris")) {
    return { request_id: "req_8f3a2c", route: "narrative" };
  }
  if (
    (q.includes("how many") || q.includes("wins") || q.includes("count")) &&
    q.includes("2023")
  ) {
    return { request_id: "req_b1d09e", route: "structured" };
  }
  if (
    q.includes("abu dhabi") ||
    q.includes("title") ||
    (q.includes("2021") && q.includes("happen"))
  ) {
    return { request_id: "req_4c77a1", route: "both" };
  }
  return { request_id: "req_demo", route: "narrative" };
}
