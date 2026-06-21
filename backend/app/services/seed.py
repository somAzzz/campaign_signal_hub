from pathlib import Path

from app.models.campaign import Campaign
from app.services.datasets import load_comment_dataset
from app.services.ingestion import (
    parse_brief,
    parse_creator_csv,
    parse_performance_csv,
    parse_products_csv,
)
from app.services.repository import repo
from app.services.signal_extractor import extract_signals

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"
SAMPLE_DIR = Path(__file__).resolve().parents[3] / "data" / "samples"


def seed_demo_data() -> Campaign:
    if repo.campaigns:
        return next(iter(repo.campaigns.values()))

    campaign = repo.add_campaign(
        Campaign(
            client="RoastHouse",
            brand="RoastHouse Coffee",
            objective=(
                "Identify taste, freshness, and positioning risks before "
                "scaling creator and paid social campaigns."
            ),
            target_audience=(
                "Keurig users, cold brew drinkers, flavor-sensitive coffee "
                "buyers, and review-led grocery shoppers."
            ),
            tone_constraints="Direct, sensory, credible, and evidence-backed.",
            required_platforms=["TikTok", "Instagram Reels", "Amazon PDP"],
        )
    )

    parse_brief(
        campaign.id,
        "coffee_campaign_brief.md",
        (FIXTURE_DIR / "coffee_campaign_brief.md").read_text(encoding="utf-8"),
    )
    load_comment_dataset(campaign.id, "coffee_50")
    parse_products_csv(
        campaign.id,
        "coffee_50_products.csv",
        (SAMPLE_DIR / "coffee_50_products.csv").read_text(encoding="utf-8"),
    )
    parse_creator_csv(
        campaign.id,
        "coffee_creator_shortlist.csv",
        (FIXTURE_DIR / "coffee_creator_shortlist.csv").read_text(encoding="utf-8"),
    )
    parse_performance_csv(
        campaign.id,
        "coffee_performance_snapshot.csv",
        (FIXTURE_DIR / "coffee_performance_snapshot.csv").read_text(encoding="utf-8"),
    )

    # Seed the review UI with LLM signals when sglang is available.
    extract_signals(campaign.id)

    return campaign
