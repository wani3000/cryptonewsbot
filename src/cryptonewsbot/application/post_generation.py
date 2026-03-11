from __future__ import annotations

from typing import Iterable, List, Optional

from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import ArticleSummary, GeneratedPost, StyleProfile
from cryptonewsbot.infrastructure.llm import LLMRewriter


def generate_posts(
    summaries: Iterable[ArticleSummary],
    style_profile: StyleProfile,
    app_config: Optional[AppConfig] = None,
) -> List[GeneratedPost]:
    rewriter = LLMRewriter(app_config) if app_config else None
    posts = []
    for summary in list(summaries)[: style_profile.max_posts]:
        headline = trim(summary.title, 80)
        body = build_post_body(summary, style_profile)
        if rewriter and rewriter.enabled:
            rewritten = try_rewrite_post(summary, style_profile, rewriter)
            if rewritten is not None:
                headline = trim(rewritten["headline"] or headline, 80)
                body = rewritten["body"] or body
                telegram_body = rewritten.get("telegram_body") or body
            else:
                telegram_body = body
        else:
            telegram_body = body
        posts.append(
            GeneratedPost(
                article_id=summary.article_id,
                headline=headline,
                body=body.strip(),
                telegram_body=fit_telegram_body(telegram_body, 1200),
            )
        )
    return posts


def build_post_body(summary: ArticleSummary, style_profile: StyleProfile) -> str:
    emoji = select_opening_emoji(summary)
    if summary.template_type == "statistical":
        text = (
            f"{emoji} {trim(summary.title, 90)}\n\n"
            f"{summary.key_point}\n\n"
            f"Key points:\n"
            f"{trim(summary.why_it_matters, 220)}\n\n"
            f"ChainBounty analysis:\n"
            f"{build_statistical_analysis(summary)}\n\n"
            f"If you're affected:\n"
            f"{build_statistical_actions()}\n\n"
            f"Source: {summary.canonical_url}"
        )
    elif summary.template_type == "discussion":
        text = (
            f"{emoji} {trim(summary.title, 90)}\n\n"
            f"{summary.key_point}\n\n"
            f"What happened:\n"
            f"{summary.why_it_matters}\n\n"
            f"ChainBounty analysis:\n"
            f"{build_discussion_analysis(summary)}\n\n"
            f"We want to hear from the community:\n"
            f"✅ Share linked wallets, routes, or counterparties\n"
            f"✅ Flag repeat tactics or reused infrastructure\n"
            f"✅ Add context from local communities or exchanges\n\n"
            f"Source: {summary.canonical_url}"
        )
    else:
        text = (
            f"{emoji} {trim(summary.title, 90)}\n\n"
            f"{summary.key_point}\n\n"
            f"What happened:\n"
            f"{build_what_happened(summary)}\n\n"
            f"ChainBounty analysis:\n"
            f"{build_incident_analysis(summary.incident_type)}\n\n"
            f"{build_secondary_section_label(summary.incident_type)}\n"
            f"{build_secondary_section(summary.incident_type)}\n\n"
            f"Protection measures:\n"
            f"{build_protection_measures(summary.incident_type)}\n\n"
            f"Source: {summary.canonical_url}"
        )

    if style_profile.preferred_cta:
        text = f"{text}\n{normalize_cta(style_profile.preferred_cta)}"
    if style_profile.hashtags:
        text = f"{text}\n\n{' '.join(style_profile.hashtags)}"
    for phrase in style_profile.forbidden_phrases:
        text = text.replace(phrase, "").strip()
    return text


def try_rewrite_post(
    summary: ArticleSummary, style_profile: StyleProfile, rewriter: LLMRewriter
) -> Optional[dict]:
    try:
        return rewriter.rewrite(
            system_prompt=build_system_prompt(style_profile),
            user_prompt=build_user_prompt(summary, style_profile),
        )
    except Exception:
        return None


def build_system_prompt(style_profile: StyleProfile) -> str:
    guidelines = "\n".join(f"- {item}" for item in style_profile.writing_guidelines)
    return (
        "You write ChainBounty-style crypto security posts for X.\n"
        f"Write in {style_profile.output_language}.\n"
        f"Tone: {style_profile.tone}.\n"
        f"Audience: {style_profile.audience}.\n"
        "Return strict JSON with keys headline, body, and telegram_body.\n"
        "body can exceed 280 characters because it may later be split into an X thread.\n"
        "telegram_body can be longer and should include fuller ChainBounty analysis while staying concise enough for Telegram.\n"
        "Avoid unsupported claims and keep facts grounded in the provided summary.\n"
        "Use active voice. Keep sentences short. Put the most important fact first.\n"
        "Be professional, factual, educational. Do not sound sensational, hyped, or emotional.\n"
        "Do not use markdown bold in the final output.\n"
        "Leave a blank line after the headline and between each section.\n"
        "Use section headers with a colon.\n"
        "Prefer security reporting language such as losses, hack, scam, wallet, MEV bot, exploit.\n"
        "Write only about crypto security incidents, scams, fraud, wallet drains, laundering, seizures, or investigations.\n"
        "Do not turn generic market news into a ChainBounty post unless the story clearly has a security, scam, or investigation angle.\n"
        "Add a ChainBounty analysis section with concrete interpretation, not a vague takeaway.\n"
        "Explain why the story matters, what bigger pattern it signals, and what users or investigators should expect next.\n"
        "Do not write vague phrases such as worth tracking, interesting case, potential risk, be careful, or stay safe.\n"
        "Protection or response steps must match the specific story, platform, region, or attack method.\n"
        "Do not attach generic wallet approval advice to regulation or policy stories unless the story is directly about wallet approvals.\n"
        "End with a community invitation and include https://community.chainbounty.io/ when space allows.\n"
        "Add one fitting emoji to the headline or opening sentence when it improves clarity.\n"
        "Use fitting emoji choices such as 🚨 for hacks, 🎣 for phishing, 🌉 for bridge exploits, "
        "🔒 for seizures or freezes, ⚠️ for scams, 📉 for statistics, and 🔍 for investigations.\n"
        "Keep the headline under 100 characters.\n"
        "When useful, follow structures like 'What happened', 'Protection measures', or concise statistical framing.\n"
        "Never use clickbait, first-person opinions, or exaggerated language.\n"
        f"Forbidden phrases: {', '.join(style_profile.forbidden_phrases) or 'none'}.\n"
        f"Writing rules:\n{guidelines or '- Keep it concise.'}"
    )


def build_user_prompt(summary: ArticleSummary, style_profile: StyleProfile) -> str:
    hashtags = " ".join(style_profile.hashtags)
    return (
        f"Template type: {summary.template_type}\n"
        f"Incident type: {summary.incident_type}\n"
        f"Title: {summary.title}\n"
        f"Key point: {summary.key_point}\n"
        f"Why it matters: {summary.why_it_matters}\n"
        f"Source: {summary.source_name}\n"
        f"URL: {summary.canonical_url}\n"
        f"Preferred CTA: {style_profile.preferred_cta or 'none'}\n"
        f"Optional hashtags: {hashtags or 'none'}\n"
        "Create a publication-ready X post and a richer Telegram post for ChainBounty.\n"
        "The ChainBounty analysis must be specific, contextual, and useful.\n"
        "Interpret the broader implication, likely next change, repeat pattern, or investigative signal.\n"
        "The response or protection section must be directly tied to this story.\n"
        "Use clear sections, blank lines, and emoji. Do not output one giant paragraph."
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
    if incident_type == "drainer":
        return (
            "The core issue is approval abuse at speed. Drainer crews often reuse wallet clusters, kit infrastructure, "
            "and lure funnels across multiple campaigns. One confirmed fund path can expose a wider victim set and help "
            "investigators map the next wave before funds fully disappear."
        )
    if incident_type == "phishing":
        return (
            "The main signal here is trust hijacking, not technical sophistication. These campaigns win by impersonating "
            "brands, support channels, or urgent account actions when users are likely to approve first and verify later. "
            "Expect the same lure format to reappear across cloned domains and social accounts."
        )
    if incident_type == "bridge_hack":
        return (
            "Bridge incidents rarely stay isolated. They expose how much risk sits in cross-chain custody, validator trust, "
            "or message verification. Once attackers break one weak point, they usually move funds quickly across chains to "
            "outrun freezes and dilute attribution."
        )
    if incident_type == "sanction_seizure":
        return (
            "This is not just a policy headline. It shows where legal pressure is reaching the laundering chain and which "
            "intermediaries may be forced to act faster. Users and platforms should expect stronger freeze, reporting, and "
            "counterparty screening standards once this kind of enforcement expands."
        )
    if incident_type == "pyramid_scam":
        return (
            "The key pattern is social engineering wrapped in fake yield logic. Pyramid operators scale through recruiter "
            "funnels and pressure tactics before funds ever touch a wallet. When the narrative depends on guaranteed returns "
            "and referral acceleration, collapse risk is structural, not accidental."
        )
    return (
        "The key question is whether this was a one-off failure or part of a repeatable playbook. ChainBounty should look "
        "for the control failure, the money movement pattern, and any sign that the same operators or methods can hit other "
        "targets next."
    )


def build_protection_measures(incident_type: str) -> str:
    if incident_type == "drainer":
        return (
            "✅ Revoke high-risk approvals on the affected wallet path immediately\n"
            "✅ Move treasury or long-term assets to a wallet with no recent dApp exposure\n"
            "✅ Share linked drainer wallets, domains, and lure pages with the ChainBounty community"
        )
    if incident_type == "phishing":
        return (
            "✅ Confirm the exact domain, support handle, and signature request before interacting\n"
            "✅ Treat urgent recovery, airdrop, or account-lock messages as hostile until verified\n"
            "✅ Bring phishing domains, screenshots, and wallet indicators to the ChainBounty community"
        )
    if incident_type == "bridge_hack":
        return (
            "✅ Reduce exposure to the affected bridge or route until root cause and remediation are confirmed\n"
            "✅ Review validator, relayer, and contract update notices before resuming transfers\n"
            "✅ Share bridge wallet traces and cross-chain fund paths with the ChainBounty community"
        )
    if incident_type == "sanction_seizure":
        return (
            "✅ Review exposure to flagged counterparties, mixers, and fast-hop routing patterns\n"
            "✅ Check whether your exchange or platform has updated freeze and reporting procedures\n"
            "✅ Discuss laundering routes and enforcement signals with the ChainBounty community"
        )
    if incident_type == "pyramid_scam":
        return (
            "✅ Treat guaranteed returns, locked withdrawals, and referral pressure as immediate red flags\n"
            "✅ Verify whether treasury, revenue, and product claims can be independently confirmed\n"
            "✅ Bring wallet clusters, recruiter trails, and payment rails to the ChainBounty community"
        )
    return (
        "✅ Identify the exact control failure before taking follow-up action\n"
        "✅ Check whether the same counterparty, wallet path, or exploit condition affects your exposure\n"
        "✅ Bring concrete indicators and suspicious patterns to the ChainBounty community"
    )


def fit_telegram_body(body: str, limit: int) -> str:
    return body


def build_what_happened(summary: ArticleSummary) -> str:
    return f"{summary.key_point}\n{summary.why_it_matters}"


def build_secondary_section_label(incident_type: str) -> str:
    if incident_type == "pyramid_scam":
        return "Red flags:"
    if incident_type in {"bridge_hack", "general"}:
        return "Root cause:"
    return "Key issue:"


def build_secondary_section(incident_type: str) -> str:
    if incident_type == "drainer":
        return (
            "Attackers relied on a wallet approval path that can be repeated across cloned lure pages and reused drainer infrastructure."
        )
    if incident_type == "phishing":
        return (
            "The weak point was trust, not code. Attackers used spoofed branding, urgency, or fake support to push approvals before verification."
        )
    if incident_type == "bridge_hack":
        return (
            "The failure likely sits in bridge verification, validator trust, or cross-chain custody design. These flaws can cascade once attackers gain one routing advantage."
        )
    if incident_type == "sanction_seizure":
        return (
            "The real issue is where enforcement is finally able to interrupt laundering flows. That creates new compliance pressure on exchanges and counterparties."
        )
    if incident_type == "pyramid_scam":
        return (
            "The business model depends on social pressure, fake returns, and recruiter incentives. Once inflows slow, the structure usually fails fast."
        )
    return "The key control failure is identifying which wallet path, approval flow, or platform weakness allowed the incident to scale."


def build_statistical_analysis(summary: ArticleSummary) -> str:
    return (
        "The data matters only if it changes how we read attacker behavior. ChainBounty should compare the move in losses, victim count, or enforcement activity against prior months to see whether defenses improved or attackers simply changed tactics."
    )


def build_statistical_actions() -> str:
    return (
        "✅ Compare the current figure against the prior reporting period\n"
        "✅ Identify which attack category drove the change\n"
        "✅ Share standout wallet clusters or sectors with the ChainBounty community"
    )


def build_discussion_analysis(summary: ArticleSummary) -> str:
    return (
        "The key value here is collective intelligence. If the public facts are incomplete, the next useful signal is usually a linked wallet, reused domain, laundering route, or prior incident pattern that the community can surface faster than a static report."
    )


def normalize_cta(cta: str) -> str:
    if "👉" in cta:
        return cta
    if "http" in cta:
        return cta.replace("https://community.chainbounty.io/", "👉 https://community.chainbounty.io/")
    return cta


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
