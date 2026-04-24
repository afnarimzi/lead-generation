"""Platform adapters for scraping different freelance platforms."""

from lead_scraper.adapters.platform_adapter import PlatformAdapter
from lead_scraper.adapters.upwork_adapter import UpworkAdapter
from lead_scraper.adapters.fiverr_adapter import FiverrAdapter
from lead_scraper.adapters.freelancer_adapter import FreelancerAdapter
from lead_scraper.adapters.peopleperhour_adapter import PeoplePerHourAdapter

__all__ = ['PlatformAdapter', 'UpworkAdapter', 'FiverrAdapter', 'FreelancerAdapter', 'PeoplePerHourAdapter']
