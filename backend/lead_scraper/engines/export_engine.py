"""Export engine for exporting leads to various formats."""

import csv
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from lead_scraper.models.lead import Lead
from lead_scraper.database.connection_manager import ConnectionManager


logger = logging.getLogger(__name__)


class ExportEngine:
    """Handles exporting leads to CSV, JSON, and Google Sheets formats."""
    
    def __init__(self, db_connection: ConnectionManager):
        """Initialize export engine with database connection.
        
        Args:
            db_connection: Database connection manager for querying leads
        """
        self.db = db_connection
    
    async def export_to_csv(
        self,
        lead_ids: Optional[list[int]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Export leads to CSV format.
        
        Args:
            lead_ids: List of specific lead IDs to export (exports all if None)
            output_path: Output file path (generates default if None)
        
        Returns:
            Path to the generated CSV file
        
        Raises:
            PermissionError: If unable to write to output path
            IOError: If file writing fails
        """
        try:
            # Fetch leads from database
            leads = self._fetch_leads(lead_ids)
            
            # Generate default output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"leads_export_{timestamp}.csv"
            
            # Ensure parent directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                if not leads:
                    # Write empty CSV with headers only
                    fieldnames = [
                        'id', 'job_title', 'job_description', 'platform_name',
                        'budget_amount', 'payment_type', 'client_info', 'job_url',
                        'posted_datetime', 'skills_tags', 'quality_score',
                        'is_potential_duplicate', 'created_at'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                else:
                    # Convert leads to dictionaries
                    lead_dicts = [lead.to_dict() for lead in leads]
                    
                    # Write CSV with data
                    fieldnames = lead_dicts[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for lead_dict in lead_dicts:
                        # Convert complex types to strings for CSV
                        if lead_dict.get('client_info'):
                            lead_dict['client_info'] = json.dumps(lead_dict['client_info'])
                        if lead_dict.get('skills_tags'):
                            lead_dict['skills_tags'] = ', '.join(lead_dict['skills_tags'])
                        writer.writerow(lead_dict)
            
            logger.info(f"Successfully exported {len(leads)} leads to CSV: {output_path}")
            return str(output_file.absolute())
            
        except PermissionError as e:
            logger.error(f"Permission denied writing to {output_path}: {e}")
            raise PermissionError(f"Unable to write to {output_path}: {e}")
        except IOError as e:
            logger.error(f"IO error writing CSV file {output_path}: {e}")
            raise IOError(f"Failed to write CSV file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error exporting to CSV: {e}", exc_info=True)
            raise

    async def export_to_json(
        self,
        lead_ids: Optional[list[int]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Export leads to JSON format.
        
        Args:
            lead_ids: List of specific lead IDs to export (exports all if None)
            output_path: Output file path (generates default if None)
        
        Returns:
            Path to the generated JSON file
        
        Raises:
            PermissionError: If unable to write to output path
            IOError: If file writing fails
        """
        try:
            # Fetch leads from database
            leads = self._fetch_leads(lead_ids)
            
            # Generate default output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"leads_export_{timestamp}.json"
            
            # Ensure parent directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert leads to dictionaries
            lead_dicts = [lead.to_dict() for lead in leads]
            
            # Write JSON file
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(lead_dicts, jsonfile, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully exported {len(leads)} leads to JSON: {output_path}")
            return str(output_file.absolute())
            
        except PermissionError as e:
            logger.error(f"Permission denied writing to {output_path}: {e}")
            raise PermissionError(f"Unable to write to {output_path}: {e}")
        except IOError as e:
            logger.error(f"IO error writing JSON file {output_path}: {e}")
            raise IOError(f"Failed to write JSON file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error exporting to JSON: {e}", exc_info=True)
            raise

    async def export_to_google_sheets(
        self,
        lead_ids: Optional[list[int]] = None,
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Leads"
    ) -> str:
        """Export leads to Google Sheets (optional integration).
        
        Args:
            lead_ids: List of specific lead IDs to export (exports all if None)
            spreadsheet_id: Google Sheets spreadsheet ID (uses default if None)
            sheet_name: Name of the sheet to append to (default: "Leads")
        
        Returns:
            URL to the Google Sheets document
        
        Raises:
            ImportError: If Google Sheets dependencies are not installed
            PermissionError: If authentication fails or access is denied
            IOError: If network error occurs during upload
        """
        try:
            # Try to import Google Sheets dependencies
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                from googleapiclient.errors import HttpError
            except ImportError as e:
                logger.warning("Google Sheets dependencies not installed")
                raise ImportError(
                    "Google Sheets export requires google-auth and google-api-python-client. "
                    "Install with: pip install google-auth google-api-python-client"
                ) from e
            
            # Fetch leads from database
            leads = self._fetch_leads(lead_ids)
            
            # Check for credentials file
            creds_path = Path("google_credentials.json")
            if not creds_path.exists():
                raise PermissionError(
                    "Google Sheets credentials file not found. "
                    "Please provide google_credentials.json with service account credentials."
                )
            
            # Authenticate with Google Sheets API
            try:
                creds = Credentials.from_service_account_file(
                    str(creds_path),
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                service = build('sheets', 'v4', credentials=creds)
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Sheets: {e}")
                raise PermissionError(f"Google Sheets authentication failed: {e}")
            
            # Use default spreadsheet ID from environment if not provided
            if spreadsheet_id is None:
                import os
                spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
                if not spreadsheet_id:
                    raise ValueError(
                        "No spreadsheet_id provided and GOOGLE_SHEETS_ID environment variable not set"
                    )
            
            # Prepare data for Google Sheets
            if not leads:
                # Just headers if no leads
                values = [[
                    'ID', 'Job Title', 'Job Description', 'Platform',
                    'Budget Amount', 'Payment Type', 'Client Info', 'Job URL',
                    'Posted Date', 'Skills Tags', 'Quality Score',
                    'Is Potential Duplicate', 'Created At'
                ]]
            else:
                # Headers + data rows
                values = [[
                    'ID', 'Job Title', 'Job Description', 'Platform',
                    'Budget Amount', 'Payment Type', 'Client Info', 'Job URL',
                    'Posted Date', 'Skills Tags', 'Quality Score',
                    'Is Potential Duplicate', 'Created At'
                ]]
                
                for lead in leads:
                    lead_dict = lead.to_dict()
                    values.append([
                        str(lead_dict.get('id', '')),
                        lead_dict.get('job_title', ''),
                        lead_dict.get('job_description', ''),
                        lead_dict.get('platform_name', ''),
                        str(lead_dict.get('budget_amount', '')),
                        lead_dict.get('payment_type', ''),
                        json.dumps(lead_dict.get('client_info', {})),
                        lead_dict.get('job_url', ''),
                        lead_dict.get('posted_datetime', ''),
                        ', '.join(lead_dict.get('skills_tags', [])),
                        str(lead_dict.get('quality_score', '')),
                        str(lead_dict.get('is_potential_duplicate', '')),
                        lead_dict.get('created_at', '')
                    ])
            
            # Append data to Google Sheets
            try:
                body = {'values': values}
                result = service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
                
                sheets_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                logger.info(f"Successfully exported {len(leads)} leads to Google Sheets: {sheets_url}")
                return sheets_url
                
            except HttpError as e:
                logger.error(f"Google Sheets API error: {e}")
                if e.resp.status == 403:
                    raise PermissionError(f"Access denied to Google Sheets: {e}")
                elif e.resp.status == 404:
                    raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
                else:
                    raise IOError(f"Google Sheets API error: {e}")
            
        except (ImportError, PermissionError, ValueError) as e:
            # Re-raise expected errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error exporting to Google Sheets: {e}", exc_info=True)
            raise IOError(f"Failed to export to Google Sheets: {e}")

    def _fetch_leads(self, lead_ids: Optional[list[int]] = None) -> list[Lead]:
        """Fetch leads from database.
        
        Args:
            lead_ids: List of specific lead IDs to fetch (fetches all if None)
        
        Returns:
            List of Lead objects
        """
        try:
            if lead_ids:
                # Fetch specific leads by ID
                placeholders = ','.join(['%s'] * len(lead_ids))
                query = f"""
                    SELECT id, job_title, job_description, platform_name, budget_amount,
                           payment_type, client_info, job_url, posted_datetime, skills_tags,
                           quality_score, is_potential_duplicate, created_at
                    FROM leads
                    WHERE id IN ({placeholders})
                    ORDER BY quality_score DESC, posted_datetime DESC
                """
                rows = self.db.execute(query, tuple(lead_ids))
            else:
                # Fetch all leads
                query = """
                    SELECT id, job_title, job_description, platform_name, budget_amount,
                           payment_type, client_info, job_url, posted_datetime, skills_tags,
                           quality_score, is_potential_duplicate, created_at
                    FROM leads
                    ORDER BY quality_score DESC, posted_datetime DESC
                """
                rows = self.db.execute(query)
            
            # Convert rows to Lead objects
            leads = [Lead.from_db_row(row) for row in rows]
            logger.info(f"Fetched {len(leads)} leads from database")
            return leads
            
        except Exception as e:
            logger.error(f"Error fetching leads from database: {e}", exc_info=True)
            raise
