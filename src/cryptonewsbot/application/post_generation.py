from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import ArticleSummary, GeneratedPost, StyleProfile, WritingStyleVariant
from cryptonewsbot.infrastructure.llm import LLMRewriter


INCIDENT_GUIDANCE = {
    "general": {
        "x_style": "Use neutral incident-reporting language and keep the post grounded in observable facts.",
        "analysis_focus": "Highlight attacker behavior, weak controls, wallet movement, and the most likely repeat pattern.",
        "telegram_depth": (
            "In telegram_body, add one extra layer on what operators should inspect next and where the risk may spread."
        ),
        "analysis": "This case is worth tracking for attacker behavior, wallet movement, and repeat victim patterns.",
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Check whether the same wallets, contracts, or distribution channels appear again\n"
            "• Track whether the incident exposes a broader control failure or a one-off operator mistake"
        ),
    },
    "drainer": {
        "x_style": "Use urgent but controlled wallet-security language centered on malicious approvals and rapid wallet emptying.",
        "analysis_focus": "Focus on approval abuse, drain speed, infrastructure reuse, and repeat wallet targeting.",
        "telegram_depth": (
            "In telegram_body, explain what wallet operators should audit next, especially approvals, linked drainers, and repeat destination paths."
        ),
        "analysis": (
            "This drainer pattern is worth tracking for malicious approvals, rapid wallet emptying, and repeat infrastructure reuse."
        ),
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Recheck fresh token approvals, suspicious spender contracts, and newly linked drain wallets\n"
            "• Watch for repeat destination clusters that suggest the same drainer kit or operator set"
        ),
    },
    "phishing": {
        "x_style": "Use warning-focused language centered on spoofed interfaces, fake support, and trust hijacking.",
        "analysis_focus": "Focus on how attackers capture trust, where the user decision point failed, and what indicators can be shared.",
        "telegram_depth": (
            "In telegram_body, add concrete operator guidance about domains, support impersonation, and reusable social engineering signals."
        ),
        "analysis": (
            "This phishing pattern is worth tracking for spoofed fronts, trust hijacking, and user decision points that attackers repeatedly exploit."
        ),
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Preserve fake domains, support handles, and signature prompts that can help cluster the campaign\n"
            "• Look for repeated lures that move victims from chat or search traffic into wallet approvals"
        ),
    },
    "bridge_hack": {
        "x_style": "Use infrastructure-risk language centered on validator trust, custody assumptions, and cross-chain exposure.",
        "analysis_focus": "Focus on validator or signer failure, custody bottlenecks, routing speed, and contagion across connected chains.",
        "telegram_depth": (
            "In telegram_body, explain what this implies for bridge users, validators, relayers, and cross-chain liquidity monitoring."
        ),
        "analysis": (
            "This bridge case is worth tracking for validator trust assumptions, cross-chain custody weak points, and how quickly attackers can route funds out."
        ),
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Monitor bridge validator, relayer, and signer updates for signs of deeper trust breakdown\n"
            "• Track whether funds are routed through fast cross-chain exits before freeze or recovery steps begin"
        ),
    },
    "sanction_seizure": {
        "x_style": "Use investigative and enforcement language centered on tracing, freezes, seizures, and compliance controls.",
        "analysis_focus": "Focus on laundering chokepoints, exchange controls, legal reach, and where enforcement is tightening onchain.",
        "telegram_depth": (
            "In telegram_body, add concise analysis on tracing pressure points, exchange response, and what this means for laundering routes."
        ),
        "analysis": (
            "This case is worth tracking for laundering pressure points, exchange compliance gaps, and where legal intervention is now reaching onchain crime."
        ),
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Trace which services, exchanges, or bridges became enforcement chokepoints in the seizure flow\n"
            "• Watch whether the action shifts laundering traffic toward smaller venues or more layered routing"
        ),
    },
    "pyramid_scam": {
        "x_style": "Use scam-exposure language centered on false returns, recruiter pressure, and victim funnel design.",
        "analysis_focus": "Focus on offchain persuasion, referral mechanics, treasury claims, and how victims are moved onchain.",
        "telegram_depth": (
            "In telegram_body, explain how the recruiting funnel works and what user-protection signals the community should preserve."
        ),
        "analysis": (
            "This scam pattern is worth tracking for false return narratives, recruiter funnels, and the offchain social layer that drives victims onchain."
        ),
        "telegram_extension": (
            "Operational watchpoints:\n"
            "• Capture recruiter promises, referral mechanics, and wallet flows that reveal the funnel design\n"
            "• Check whether treasury, yield, or product claims collapse when compared against actual onchain movement"
        ),
    },
}

CHAINBOUNTY_COMPANY_CONTEXT = (
    "ChainBounty is a community-powered crypto crime investigation platform. "
    "We help victims, researchers, and security operators report scams and hacks, trace wallet movement, "
    "surface attacker patterns, and coordinate intelligence with the wider community."
)

TEMPLATE_GUIDANCE = {
    "incident": (
        "Use an incident-report structure. Start with the concrete fact, then add a short ChainBounty analyst takeaway."
    ),
    "statistical": (
        "Use a data-report structure. Lead with the main figure and comparison point, then explain the implication without hype."
    ),
    "discussion": (
        "Use an investigation prompt structure. Present the known facts, the unresolved issue, and invite specific community input."
    ),
}

DEFAULT_WRITING_STYLE_VARIANTS = [
    WritingStyleVariant(
        name="incident_briefing",
        x_instruction="Use a crisp analyst briefing style with a fact-first opening and a clean 'What happened' structure.",
        telegram_instruction="Keep the Telegram post structured like a concise incident brief with analyst commentary and operational watchpoints.",
    ),
    WritingStyleVariant(
        name="operator_alert",
        x_instruction="Use an operator alert style that frames the story as an active risk signal with practical actions.",
        telegram_instruction="Write Telegram like an operator notice with stronger action labels and immediate defensive focus.",
    ),
    WritingStyleVariant(
        name="casefile_note",
        x_instruction="Use a casefile style that reads like ChainBounty is logging an investigation note on the incident.",
        telegram_instruction="Write Telegram like a casefile update with investigation angle, observed pattern, and next checks.",
    ),
    WritingStyleVariant(
        name="community_watch",
        x_instruction="Use a community-watch style that emphasizes shared signals, repeated attacker patterns, and reporting value.",
        telegram_instruction="Write Telegram like a community investigation prompt with clearer asks and shared-defense framing.",
    ),
]

WRITING_STYLE_LABELS = {
    "incident_briefing": {
        "incident_x_fact_label": "What happened",
        "incident_x_analysis_label": "ChainBounty view",
        "incident_x_actions_label": "Protection measures",
        "incident_tg_fact_label": "What happened",
        "incident_tg_analysis_label": "ChainBounty analysis",
        "incident_tg_actions_label": "Protection measures",
        "stat_x_metric_label": "Key figures",
        "stat_x_analysis_label": "ChainBounty view",
        "discussion_x_issue_label": "But here's the issue",
        "discussion_x_analysis_label": "ChainBounty view",
    },
    "operator_alert": {
        "incident_x_fact_label": "Risk signal",
        "incident_x_analysis_label": "Why ChainBounty is watching",
        "incident_x_actions_label": "Operator actions",
        "incident_tg_fact_label": "Risk signal",
        "incident_tg_analysis_label": "Why operators should care",
        "incident_tg_actions_label": "Immediate actions",
        "stat_x_metric_label": "Signal shift",
        "stat_x_analysis_label": "Why ChainBounty is watching",
        "discussion_x_issue_label": "Operator question",
        "discussion_x_analysis_label": "ChainBounty read",
    },
    "casefile_note": {
        "incident_x_fact_label": "Case file",
        "incident_x_analysis_label": "ChainBounty read",
        "incident_x_actions_label": "Next checks",
        "incident_tg_fact_label": "Case file",
        "incident_tg_analysis_label": "Investigation angle",
        "incident_tg_actions_label": "Next checks",
        "stat_x_metric_label": "Case signal",
        "stat_x_analysis_label": "ChainBounty read",
        "discussion_x_issue_label": "Open question",
        "discussion_x_analysis_label": "Investigation angle",
    },
    "community_watch": {
        "incident_x_fact_label": "Watchpoint",
        "incident_x_analysis_label": "Community angle",
        "incident_x_actions_label": "Defense steps",
        "incident_tg_fact_label": "Watchpoint",
        "incident_tg_analysis_label": "Community investigation angle",
        "incident_tg_actions_label": "Defense steps",
        "stat_x_metric_label": "Trend watch",
        "stat_x_analysis_label": "Community angle",
        "discussion_x_issue_label": "What the community should watch",
        "discussion_x_analysis_label": "Investigation prompt",
    },
}

WRITING_STYLE_COPY = {
    "incident_briefing": {
        "x_opening": "{emoji} {title}",
        "telegram_opening": "{emoji} {title}",
        "incident_x_analysis_text": "{analysis}",
        "incident_tg_analysis_text": "{analysis}",
    },
    "operator_alert": {
        "x_opening": "{emoji} Operator alert: {title}",
        "telegram_opening": "{emoji} Operator alert: {title}",
        "incident_x_analysis_text": "ChainBounty is treating this as an operator-facing risk signal: {analysis}",
        "incident_tg_analysis_text": "ChainBounty is treating this as an active operator watch item: {analysis}",
    },
    "casefile_note": {
        "x_opening": "{emoji} Case note: {title}",
        "telegram_opening": "{emoji} Case note: {title}",
        "incident_x_analysis_text": "Current ChainBounty case read: {analysis}",
        "incident_tg_analysis_text": "Current ChainBounty investigation read: {analysis}",
    },
    "community_watch": {
        "x_opening": "{emoji} Community watch: {title}",
        "telegram_opening": "{emoji} Community watch: {title}",
        "incident_x_analysis_text": "What the ChainBounty community should watch next: {analysis}",
        "incident_tg_analysis_text": "What the ChainBounty community should watch next: {analysis}",
    },
}


def generate_posts(
    summaries: Iterable[ArticleSummary],
    style_profile: StyleProfile,
    app_config: Optional[AppConfig] = None,
    writing_style_rotation_seed: int | None = None,
) -> List[GeneratedPost]:
    rewriter = LLMRewriter(app_config) if app_config else None
    selected_summaries = list(summaries)[: style_profile.max_posts]
    style_variants = assign_writing_style_variants(
        selected_summaries,
        resolve_writing_style_variants(style_profile),
        rotation_seed=writing_style_rotation_seed,
    )
    posts = []
    for summary, style_variant in zip(selected_summaries, style_variants):
        headline = trim(summary.title, 80)
        body = build_post_body(summary, style_profile, style_variant)
        telegram_body = build_telegram_body(summary, style_profile, style_variant)
        if rewriter and rewriter.enabled:
            rewritten = try_rewrite_post(summary, style_profile, style_variant, rewriter)
            if rewritten is not None:
                headline = trim(strip_markdown_emphasis(rewritten["headline"] or headline), 80)
                body = strip_markdown_emphasis(rewritten["body"] or body)
                telegram_body = strip_markdown_emphasis(rewritten.get("telegram_body") or body)
        posts.append(
            GeneratedPost(
                article_id=summary.article_id,
                headline=strip_markdown_emphasis(headline),
                body=strip_markdown_emphasis(body).strip(),
                telegram_body=fit_telegram_body(strip_markdown_emphasis(telegram_body)),
                writing_style_name=style_variant.name,
            )
        )
    return posts


def build_post_body(summary: ArticleSummary, style_profile: StyleProfile, style_variant: WritingStyleVariant) -> str:
    emoji = select_opening_emoji(summary)
    labels = resolve_style_labels(style_variant.name)
    copy = resolve_style_copy(style_variant.name)
    if summary.template_type == "statistical":
        text = (
            f"{render_opening(summary, style_variant.name, emoji, telegram=False)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['stat_x_metric_label']}:\n"
            f"• {trim(summary.why_it_matters, 120)}\n\n"
            f"{labels['stat_x_analysis_label']}:\n"
            f"Track whether the same attack pattern, laundering route, or victim profile appears again.\n\n"
            f"Source: {summary.canonical_url}"
        )
    elif summary.template_type == "discussion":
        text = (
            f"{render_opening(summary, style_variant.name, emoji, telegram=False)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['discussion_x_issue_label']}:\n"
            f"{summary.why_it_matters}\n\n"
            f"{labels['discussion_x_analysis_label']}:\n"
            f"If you have seen linked wallets, reuse patterns, or laundering paths, bring them into the community discussion.\n\n"
            f"Source: {summary.canonical_url}"
        )
    else:
        text = (
            f"{render_opening(summary, style_variant.name, emoji, telegram=False)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['incident_x_fact_label']}:\n"
            f"• {trim(summary.key_point, 90)}\n"
            f"• {trim(summary.why_it_matters, 90)}\n\n"
            f"{labels['incident_x_analysis_label']}:\n"
            f"{copy['incident_x_analysis_text'].format(analysis=build_incident_analysis(summary.incident_type))}\n\n"
            f"{labels['incident_x_actions_label']}:\n"
            f"{build_protection_measures(summary.incident_type)}\n\n"
            f"Source: {summary.canonical_url}"
        )

    if style_profile.preferred_cta:
        text = f"{text}\n{style_profile.preferred_cta}"
    if style_profile.signature:
        text = f"{text}\n{style_profile.signature}"
    if style_profile.hashtags:
        text = f"{text}\n{' '.join(style_profile.hashtags)}"
    for phrase in style_profile.forbidden_phrases:
        text = text.replace(phrase, "").strip()
    return text


def build_telegram_body(
    summary: ArticleSummary, style_profile: StyleProfile, style_variant: WritingStyleVariant
) -> str:
    base_text = build_post_body(summary, style_profile, style_variant)
    labels = resolve_style_labels(style_variant.name)
    copy = resolve_style_copy(style_variant.name)
    if summary.template_type == "statistical":
        text = (
            f"{render_opening(summary, style_variant.name, select_opening_emoji(summary), telegram=True)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['stat_x_metric_label']}:\n"
            f"• {summary.why_it_matters}\n\n"
            f"{labels['incident_tg_analysis_label']}:\n"
            "Look for which attack categories, victim segments, or laundering routes are accelerating rather than treating the headline number in isolation.\n\n"
            "Why operators should care:\n"
            "Use the trend shift to prioritize which scam or exploit patterns need faster reporting and monitoring.\n\n"
            f"Source: {summary.canonical_url}"
        )
    elif summary.template_type == "discussion":
        text = (
            f"{render_opening(summary, style_variant.name, select_opening_emoji(summary), telegram=True)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['discussion_x_issue_label']}:\n"
            f"{summary.why_it_matters}\n\n"
            "Possible scenarios:\n"
            "1. The attacker reused a known playbook and left traceable wallet links\n"
            "2. A service-side control failed and the public facts still lag the actual blast radius\n"
            "3. Offchain social engineering or insider access played a larger role than first reported\n\n"
            "We want to hear from the community:\n"
            "• Wallet traces or linked addresses\n"
            "• Reused infrastructure or fake support fronts\n"
            "• Recovery, freeze, or attribution signals\n\n"
            f"Source: {summary.canonical_url}"
        )
    else:
        subtype_guide = get_incident_guidance(summary.incident_type)
        text = (
            f"{render_opening(summary, style_variant.name, select_opening_emoji(summary), telegram=True)}\n\n"
            f"{summary.key_point}\n\n"
            f"{labels['incident_tg_fact_label']}:\n"
            f"• {summary.key_point}\n"
            f"• {summary.why_it_matters}\n\n"
            f"{labels['incident_tg_analysis_label']}:\n"
            f"{copy['incident_tg_analysis_text'].format(analysis=subtype_guide['analysis'])}\n\n"
            f"{subtype_guide['telegram_extension']}\n\n"
            f"{labels['incident_tg_actions_label']}:\n"
            f"{build_protection_measures(summary.incident_type)}\n\n"
            f"Source: {summary.canonical_url}"
        )
    if style_profile.preferred_cta:
        text = f"{text}\n{style_profile.preferred_cta}"
    if style_profile.signature:
        text = f"{text}\n{style_profile.signature}"
    if style_profile.hashtags:
        text = f"{text}\n{' '.join(style_profile.hashtags)}"
    for phrase in style_profile.forbidden_phrases:
        text = text.replace(phrase, "").strip()
    if len(text) <= len(base_text):
        return base_text
    return text


def try_rewrite_post(
    summary: ArticleSummary,
    style_profile: StyleProfile,
    style_variant: WritingStyleVariant,
    rewriter: LLMRewriter,
) -> Optional[dict]:
    try:
        return rewriter.rewrite(
            system_prompt=build_system_prompt(summary, style_profile, style_variant),
            user_prompt=build_user_prompt(summary, style_profile, style_variant),
        )
    except Exception:
        return None


def build_system_prompt(
    summary: ArticleSummary, style_profile: StyleProfile, style_variant: WritingStyleVariant
) -> str:
    guidelines = "\n".join(f"- {item}" for item in style_profile.writing_guidelines)
    template_guidance = TEMPLATE_GUIDANCE.get(summary.template_type, TEMPLATE_GUIDANCE["incident"])
    subtype_guidance = get_incident_guidance(summary.incident_type)
    return (
        "You write ChainBounty-style crypto security posts for X.\n"
        f"Company context: {CHAINBOUNTY_COMPANY_CONTEXT}\n"
        f"Write in {style_profile.output_language}.\n"
        f"Tone: {style_profile.tone}.\n"
        f"Audience: {style_profile.audience}.\n"
        "Write from ChainBounty's company perspective, like the investigations and security team is briefing the community.\n"
        "Do not sound like a neutral wire service or generic news account.\n"
        "Center the post on what the incident means for victim support, wallet tracing, attacker behavior, reporting signals, and community investigation value.\n"
        f"Assigned writing style: {style_variant.name}.\n"
        f"X style variant instruction: {style_variant.x_instruction or 'Use the assigned style consistently.'}\n"
        f"Telegram style variant instruction: {style_variant.telegram_instruction or 'Use the assigned style consistently.'}\n"
        "Return strict JSON with keys headline, body, and telegram_body.\n"
        "body can exceed 280 characters because it may later be split into an X thread.\n"
        "telegram_body can be longer and should include fuller ChainBounty analysis while staying concise enough for Telegram.\n"
        "Avoid unsupported claims and keep facts grounded in the provided summary.\n"
        "Use active voice. Keep sentences short. Put the most important fact first.\n"
        "Be professional, factual, educational. Do not sound sensational, hyped, or emotional.\n"
        "Prefer security reporting language such as losses, hack, scam, wallet, MEV bot, exploit.\n"
        "Write only about crypto security incidents, scams, fraud, wallet drains, laundering, seizures, or investigations.\n"
        "Do not turn generic market news into a ChainBounty post unless the story clearly has a security, scam, or investigation angle.\n"
        "Add a short ChainBounty analyst takeaway, not just a summary.\n"
        "End with a community invitation and include https://community.chainbounty.io/ when space allows.\n"
        "Add one fitting emoji to the headline or opening sentence when it improves clarity.\n"
        "Use fitting emoji choices such as 🚨 for hacks, 🎣 for phishing, 🌉 for bridge exploits, "
        "🔒 for seizures or freezes, ⚠️ for scams, 📉 for statistics, and 🔍 for investigations.\n"
        "Keep the headline under 100 characters.\n"
        "When useful, follow structures like 'What happened', 'Protection measures', or concise statistical framing.\n"
        f"Template guidance: {template_guidance}\n"
        f"Subtype X style: {subtype_guidance['x_style']}\n"
        f"Subtype analyst focus: {subtype_guidance['analysis_focus']}\n"
        f"Subtype Telegram depth: {subtype_guidance['telegram_depth']}\n"
        "Keep body tighter and more front-loaded for X. Use telegram_body to add one more layer of concrete analysis, watchpoints, or operator implications.\n"
        "Never use clickbait, first-person opinions, or exaggerated language.\n"
        f"Forbidden phrases: {', '.join(style_profile.forbidden_phrases) or 'none'}.\n"
        f"Writing rules:\n{guidelines or '- Keep it concise.'}"
    )


def build_user_prompt(
    summary: ArticleSummary, style_profile: StyleProfile, style_variant: WritingStyleVariant
) -> str:
    hashtags = " ".join(style_profile.hashtags)
    template_guidance = TEMPLATE_GUIDANCE.get(summary.template_type, TEMPLATE_GUIDANCE["incident"])
    subtype_guidance = get_incident_guidance(summary.incident_type)
    return (
        f"Company context: {CHAINBOUNTY_COMPANY_CONTEXT}\n"
        f"Assigned writing style: {style_variant.name}\n"
        f"X style instruction: {style_variant.x_instruction or 'none'}\n"
        f"Telegram style instruction: {style_variant.telegram_instruction or 'none'}\n"
        f"Template type: {summary.template_type}\n"
        f"Incident type: {summary.incident_type}\n"
        f"Cluster size: {summary.cluster_size}\n"
        f"Related sources: {', '.join(summary.related_sources) or 'none'}\n"
        f"Title: {summary.title}\n"
        f"Key point: {summary.key_point}\n"
        f"Why it matters: {summary.why_it_matters}\n"
        f"Source: {summary.source_name}\n"
        f"URL: {summary.canonical_url}\n"
        f"Preferred CTA: {style_profile.preferred_cta or 'none'}\n"
        f"Optional hashtags: {hashtags or 'none'}\n"
        f"Template guidance: {template_guidance}\n"
        f"Subtype X style: {subtype_guidance['x_style']}\n"
        f"Subtype analyst focus: {subtype_guidance['analysis_focus']}\n"
        f"Subtype Telegram depth: {subtype_guidance['telegram_depth']}\n"
        "Create a publication-ready X post and a richer Telegram post for ChainBounty with a stronger security-analysis angle."
    )


def select_opening_emoji(summary: ArticleSummary) -> str:
    if summary.template_type == "statistical":
        return "📉"
    if summary.template_type == "discussion":
        return "🔍"
    if summary.incident_type in {"drainer", "phishing", "bridge_hack"}:
        return "🚨"
    if summary.incident_type == "sanction_seizure":
        return "🔍"
    if summary.incident_type == "pyramid_scam":
        return "⚠️"
    haystack = " ".join([summary.title, summary.key_point, summary.why_it_matters]).lower()
    if any(keyword in haystack for keyword in ["hack", "scam", "exploit", "attack", "phishing", "breach"]):
        return "🚨"
    if any(keyword in haystack for keyword in ["warning", "protect", "risk", "fake"]):
        return "⚠️"
    if any(keyword in haystack for keyword in ["stat", "%", "decrease", "increase", "monthly", "year-over-year"]):
        return "📉"
    if any(keyword in haystack for keyword in ["investigation", "probe", "trace", "launder", "wallet"]):
        return "🔍"
    return "📊"


def trim(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_incident_analysis(incident_type: str) -> str:
    return str(get_incident_guidance(incident_type)["analysis"])


def get_incident_guidance(incident_type: str) -> dict[str, str]:
    return INCIDENT_GUIDANCE.get(incident_type, INCIDENT_GUIDANCE["general"])


def build_protection_measures(incident_type: str) -> str:
    if incident_type == "drainer":
        return (
            "✅ Revoke risky approvals and review wallet permissions\n"
            "✅ Separate trading wallets from treasury wallets\n"
            "✅ Report linked drainer wallets to the ChainBounty community"
        )
    if incident_type == "phishing":
        return (
            "✅ Verify domains, support channels, and signatures before acting\n"
            "✅ Never enter seed phrases or approve blind prompts\n"
            "✅ Share phishing indicators with the ChainBounty community"
        )
    if incident_type == "bridge_hack":
        return (
            "✅ Reduce bridge exposure during active incidents\n"
            "✅ Track validator, relayer, and contract update notices\n"
            "✅ Bring bridge wallet traces to the ChainBounty community"
        )
    if incident_type == "sanction_seizure":
        return (
            "✅ Monitor sanctioned wallets and suspicious routing paths\n"
            "✅ Review exchange controls around freeze and reporting flows\n"
            "✅ Discuss laundering patterns with the ChainBounty community"
        )
    if incident_type == "pyramid_scam":
        return (
            "✅ Treat guaranteed returns and referral pressure as red flags\n"
            "✅ Verify treasury, product, and revenue claims before funding\n"
            "✅ Bring wallet clusters and recruiter trails to the ChainBounty community"
        )
    return (
        "✅ Verify the source before signing or sending funds\n"
        "✅ Check wallet approvals and destination addresses\n"
        "✅ Bring suspicious patterns to the ChainBounty community"
    )


def fit_telegram_body(body: str) -> str:
    return body.strip()


def strip_markdown_emphasis(value: str) -> str:
    return value.replace("**", "").strip()


def split_x_thread(body: str, limit: int = 280) -> List[str]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return [body]
    chunks: List[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n\n{line}".strip() if current else line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = line
            continue
        words = line.split()
        piece = ""
        for word in words:
            candidate_piece = f"{piece} {word}".strip()
            if len(candidate_piece) <= limit:
                piece = candidate_piece
            else:
                chunks.append(piece)
                piece = word
        current = piece
    if current:
        chunks.append(current)
    return chunks


def resolve_writing_style_variants(style_profile: StyleProfile) -> List[WritingStyleVariant]:
    variants = [variant for variant in style_profile.writing_style_variants if variant.name.strip()]
    if variants:
        return variants
    return DEFAULT_WRITING_STYLE_VARIANTS


def assign_writing_style_variants(
    summaries: List[ArticleSummary],
    variants: List[WritingStyleVariant],
    rotation_seed: int | None = None,
) -> List[WritingStyleVariant]:
    if not variants:
        variants = DEFAULT_WRITING_STYLE_VARIANTS
    if rotation_seed is None:
        rotation_seed = datetime.now(timezone.utc).date().toordinal()
    start_index = rotation_seed % len(variants)
    return [variants[(start_index + index) % len(variants)] for index, _ in enumerate(summaries)]


def resolve_next_writing_style_start_index(
    variants: List[WritingStyleVariant],
    last_style_name: str,
    fallback_seed: int | None = None,
) -> int:
    if not variants:
        return 0
    if last_style_name:
        for index, variant in enumerate(variants):
            if variant.name == last_style_name:
                return (index + 1) % len(variants)
    if fallback_seed is None:
        fallback_seed = datetime.now(timezone.utc).date().toordinal()
    return fallback_seed % len(variants)


def resolve_style_labels(style_name: str) -> dict[str, str]:
    return WRITING_STYLE_LABELS.get(style_name, WRITING_STYLE_LABELS["incident_briefing"])


def resolve_style_copy(style_name: str) -> dict[str, str]:
    return WRITING_STYLE_COPY.get(style_name, WRITING_STYLE_COPY["incident_briefing"])


def render_opening(summary: ArticleSummary, style_name: str, emoji: str, telegram: bool) -> str:
    template_key = "telegram_opening" if telegram else "x_opening"
    copy = resolve_style_copy(style_name)
    return copy[template_key].format(emoji=emoji, title=trim(summary.title, 90))
