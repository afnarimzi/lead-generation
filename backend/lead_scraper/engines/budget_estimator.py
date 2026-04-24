"""
Budget estimation engine for jobs with missing budget information.
"""
import logging
import re
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BudgetEstimate:
    """Budget estimate with confidence score."""
    amount: float
    confidence: float  # 0.0 to 1.0
    method: str  # How the estimate was derived
    

class BudgetEstimator:
    """
    Estimates budget for jobs with missing budget information.
    
    Uses multiple heuristics:
    1. Skill-based estimation
    2. Job complexity analysis
    3. Platform-specific patterns
    4. Historical data (if available)
    """
    
    def __init__(self):
        """Initialize budget estimator with skill-based rates."""
        # Skill-based hourly rates (USD)
        self.skill_rates = {
            # High-value skills
            'machine learning': 75,
            'artificial intelligence': 80,
            'ai': 80,
            'deep learning': 85,
            'data science': 70,
            'blockchain': 90,
            'cryptocurrency': 85,
            'cloud architecture': 80,
            'devops': 65,
            'kubernetes': 70,
            'aws': 65,
            'azure': 65,
            'google cloud': 65,
            
            # Programming languages
            'python': 60,
            'javascript': 55,
            'react': 60,
            'node.js': 58,
            'java': 55,
            'c++': 65,
            'go': 70,
            'rust': 75,
            'swift': 65,
            'kotlin': 60,
            
            # Web development
            'web development': 50,
            'frontend': 50,
            'backend': 55,
            'full stack': 60,
            'wordpress': 35,
            'shopify': 40,
            'magento': 45,
            
            # Mobile development
            'mobile app': 60,
            'ios': 65,
            'android': 60,
            'flutter': 55,
            'react native': 58,
            
            # Design
            'ui/ux': 50,
            'graphic design': 40,
            'web design': 45,
            'logo design': 35,
            'branding': 50,
            
            # Content & Marketing
            'content writing': 25,
            'copywriting': 35,
            'seo': 40,
            'digital marketing': 45,
            'social media': 30,
            
            # Data & Analytics
            'data analysis': 55,
            'excel': 30,
            'sql': 50,
            'tableau': 55,
            'power bi': 50,
            
            # Other
            'virtual assistant': 15,
            'data entry': 10,
            'translation': 20,
            'transcription': 15,
        }
        
        # Complexity multipliers
        self.complexity_multipliers = {
            'simple': 0.7,
            'basic': 0.8,
            'intermediate': 1.0,
            'advanced': 1.3,
            'complex': 1.5,
            'enterprise': 1.8,
        }
        
        # Platform-specific adjustments
        self.platform_adjustments = {
            'upwork': 1.0,
            'freelancer': 0.85,  # Generally lower rates
            'fiverr': 0.7,       # Lower rates, more competition
            'peopleperhour': 0.9,
        }
    
    def estimate_budget(
        self,
        job_title: str,
        job_description: str,
        skills: List[str],
        platform: str = 'upwork'
    ) -> Optional[BudgetEstimate]:
        """
        Estimate budget for a job based on available information.
        
        Args:
            job_title: Job title
            job_description: Job description
            skills: List of required skills
            platform: Platform name
            
        Returns:
            BudgetEstimate or None if estimation not possible
        """
        try:
            # Combine all text for analysis
            full_text = f"{job_title} {job_description}".lower()
            
            # Method 1: Skill-based estimation
            skill_estimate = self._estimate_from_skills(skills, full_text)
            
            # Method 2: Complexity-based estimation
            complexity_estimate = self._estimate_from_complexity(full_text)
            
            # Method 3: Duration-based estimation
            duration_estimate = self._estimate_from_duration(full_text)
            
            # Method 4: Project type estimation
            type_estimate = self._estimate_from_project_type(full_text)
            
            # Combine estimates
            estimates = [e for e in [skill_estimate, complexity_estimate, duration_estimate, type_estimate] if e]
            
            if not estimates:
                return None
            
            # Weighted average based on confidence
            total_weight = sum(e.confidence for e in estimates)
            if total_weight == 0:
                return None
            
            weighted_amount = sum(e.amount * e.confidence for e in estimates) / total_weight
            avg_confidence = sum(e.confidence for e in estimates) / len(estimates)
            
            # Apply platform adjustment
            platform_adj = self.platform_adjustments.get(platform.lower(), 1.0)
            final_amount = weighted_amount * platform_adj
            
            # Ensure reasonable range
            final_amount = max(50, min(50000, final_amount))
            
            return BudgetEstimate(
                amount=final_amount,
                confidence=avg_confidence * 0.7,  # Reduce confidence for estimates
                method=f"Combined estimation from {len(estimates)} methods"
            )
            
        except Exception as e:
            logger.debug(f"Error estimating budget: {e}")
            return None
    
    def _estimate_from_skills(self, skills: List[str], full_text: str) -> Optional[BudgetEstimate]:
        """Estimate budget based on required skills."""
        if not skills:
            return None
        
        try:
            # Find matching skills and their rates
            matched_rates = []
            for skill in skills:
                skill_lower = skill.lower().strip()
                if skill_lower in self.skill_rates:
                    matched_rates.append(self.skill_rates[skill_lower])
            
            # Also check for skills mentioned in text
            for skill, rate in self.skill_rates.items():
                if skill in full_text:
                    matched_rates.append(rate)
            
            if not matched_rates:
                return None
            
            # Use highest rate (most valuable skill)
            max_rate = max(matched_rates)
            avg_rate = sum(matched_rates) / len(matched_rates)
            
            # Estimate project duration (default: 40 hours)
            estimated_hours = self._estimate_hours_from_text(full_text)
            
            # Calculate budget
            budget = max_rate * estimated_hours
            
            # Confidence based on number of matched skills
            confidence = min(0.8, len(matched_rates) * 0.2)
            
            return BudgetEstimate(
                amount=budget,
                confidence=confidence,
                method=f"Skill-based ({len(matched_rates)} skills matched)"
            )
            
        except Exception as e:
            logger.debug(f"Error in skill-based estimation: {e}")
            return None
    
    def _estimate_from_complexity(self, full_text: str) -> Optional[BudgetEstimate]:
        """Estimate budget based on project complexity indicators."""
        try:
            # Complexity indicators
            complexity_indicators = {
                'simple': ['simple', 'basic', 'easy', 'quick', 'small'],
                'intermediate': ['moderate', 'standard', 'typical', 'regular'],
                'advanced': ['advanced', 'complex', 'sophisticated', 'professional'],
                'enterprise': ['enterprise', 'large scale', 'corporate', 'mission critical']
            }
            
            # Find complexity level
            complexity_level = 'intermediate'  # default
            max_matches = 0
            
            for level, indicators in complexity_indicators.items():
                matches = sum(1 for indicator in indicators if indicator in full_text)
                if matches > max_matches:
                    max_matches = matches
                    complexity_level = level
            
            # Base budget for intermediate complexity
            base_budget = 2000
            multiplier = self.complexity_multipliers.get(complexity_level, 1.0)
            
            budget = base_budget * multiplier
            confidence = 0.4 if max_matches > 0 else 0.2
            
            return BudgetEstimate(
                amount=budget,
                confidence=confidence,
                method=f"Complexity-based ({complexity_level})"
            )
            
        except Exception as e:
            logger.debug(f"Error in complexity-based estimation: {e}")
            return None
    
    def _estimate_from_duration(self, full_text: str) -> Optional[BudgetEstimate]:
        """Estimate budget based on project duration indicators."""
        try:
            # Duration patterns
            duration_patterns = {
                r'(\d+)\s*hours?': lambda h: int(h),
                r'(\d+)\s*days?': lambda d: int(d) * 8,
                r'(\d+)\s*weeks?': lambda w: int(w) * 40,
                r'(\d+)\s*months?': lambda m: int(m) * 160,
            }
            
            estimated_hours = None
            
            for pattern, converter in duration_patterns.items():
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    estimated_hours = converter(match.group(1))
                    break
            
            if not estimated_hours:
                return None
            
            # Use average hourly rate
            avg_rate = 50  # USD per hour
            budget = estimated_hours * avg_rate
            
            return BudgetEstimate(
                amount=budget,
                confidence=0.6,
                method=f"Duration-based ({estimated_hours} hours)"
            )
            
        except Exception as e:
            logger.debug(f"Error in duration-based estimation: {e}")
            return None
    
    def _estimate_from_project_type(self, full_text: str) -> Optional[BudgetEstimate]:
        """Estimate budget based on project type."""
        try:
            # Project type budgets (typical ranges)
            project_types = {
                'website': 2500,
                'web app': 5000,
                'mobile app': 8000,
                'logo': 300,
                'branding': 1500,
                'data analysis': 1200,
                'machine learning': 4000,
                'ai': 5000,
                'chatbot': 2000,
                'api': 3000,
                'database': 2500,
                'ecommerce': 4000,
                'wordpress': 1500,
                'shopify': 2000,
            }
            
            # Find matching project type
            for project_type, budget in project_types.items():
                if project_type in full_text:
                    return BudgetEstimate(
                        amount=budget,
                        confidence=0.5,
                        method=f"Project type ({project_type})"
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in project type estimation: {e}")
            return None
    
    def _estimate_hours_from_text(self, full_text: str) -> int:
        """Estimate project hours from text description."""
        # Look for explicit hour mentions
        hour_patterns = [
            r'(\d+)\s*hours?',
            r'(\d+)\s*hrs?',
        ]
        
        for pattern in hour_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Look for day/week mentions
        if re.search(r'\d+\s*days?', full_text, re.IGNORECASE):
            day_match = re.search(r'(\d+)\s*days?', full_text, re.IGNORECASE)
            if day_match:
                return int(day_match.group(1)) * 8
        
        if re.search(r'\d+\s*weeks?', full_text, re.IGNORECASE):
            week_match = re.search(r'(\d+)\s*weeks?', full_text, re.IGNORECASE)
            if week_match:
                return int(week_match.group(1)) * 40
        
        # Default estimation based on complexity indicators
        if any(word in full_text for word in ['simple', 'quick', 'small', 'basic']):
            return 20
        elif any(word in full_text for word in ['complex', 'large', 'advanced', 'enterprise']):
            return 120
        else:
            return 40  # Default: 1 week