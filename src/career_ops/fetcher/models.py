from dataclasses import dataclass

@dataclass
class JobPosting:
    url: str
    description: str
    company: str
    role: str

    def to_csv_row(self, job_id: int, date: str) -> dict:
        """Format to match job-tracker.csv schema"""
        return {
            "ID": str(job_id),
            "URL": self.url,
            "Job Description": self.description,
            "Company": self.company,
            "Position": self.role,
            "Processing Date": date
        }
