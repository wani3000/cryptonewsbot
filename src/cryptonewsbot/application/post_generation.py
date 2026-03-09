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
            f"{emoji} **{trim(summary.title, 90)}**\n\n"
            f"{summary.key_point}\n\n"
            f"**Key figures:**\n"
            f"• {trim(summary.why_it_matters, 120)}\n\n"
            f"**ChainBounty view:**\n"
            f"Track whether the same attack pattern, laundering route, or victim profile appears again.\n\n"
            f"Source: {summary.canonical_url}"
        )
    elif summary.template_type == "discussion":
        text = (
            f"{emoji} **{trim(summary.title, 90)}**\n\n"
            f"{summary.key_point}\n\n"
            f"**But here's the issue:**\n"
            f"{summary.why_it_matters}\n\n"
            f"**ChainBounty view:**\n"
            f"If you have seen linked wallets, reuse patterns, or laundering paths, bring them into the community discussion.\n\n"
            f"Source: {summary.canonical_url}"
        )
    else:
        text = (
            f"{emoji} **{trim(summary.title, 90)}**\n\n"
            f"{summary.key_point}\n\n"
            f"**What happened:**\n"
            f"• {trim(summary.key_point, 90)}\n"
            f"• {trim(summary.why_it_matters, 90)}\n\n"
            f"**ChainBounty view:**\n"
            f"{build_incident_analysis(summary.incident_type)}\n\n"
            f"**Protection measures:**\n"
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
    if incident_type == "drainer":
        return (
            "This drainer pattern is worth tracking for malicious approvals, rapid wallet emptying, "
            "and repeat infrastructure reuse."
        )
    if incident_type == "phishing":
        return (
            "This phishing pattern is worth tracking for spoofed fronts, trust hijacking, and user decision points "
            "that attackers repeatedly exploit."
        )
    if incident_type == "bridge_hack":
        return (
            "This bridge case is worth tracking for validator trust assumptions, cross-chain custody weak points, "
            "and how quickly attackers can route funds out."
        )
    if incident_type == "sanction_seizure":
        return (
            "This case is worth tracking for laundering pressure points, exchange compliance gaps, and where legal "
            "intervention is now reaching onchain crime."
        )
    if incident_type == "pyramid_scam":
        return (
            "This scam pattern is worth tracking for false return narratives, recruiter funnels, and the offchain "
            "social layer that drives victims onchain."
        )
    return "This case is worth tracking for attacker behavior, wallet movement, and repeat victim patterns."


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


def fit_telegram_body(body: str, limit: int) -> str:
    if len(body) <= limit:
        return body
    return trim(body, limit)


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
