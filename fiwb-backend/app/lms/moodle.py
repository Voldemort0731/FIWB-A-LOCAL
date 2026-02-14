import httpx
import logging

logger = logging.getLogger("uvicorn.error")

class MoodleClient:
    def __init__(self, moodle_url: str, moodle_token: str):
        # Ensure url doesn't end with / and includes rest/server.php
        self.base_url = moodle_url.rstrip('/')
        if not self.base_url.endswith('webservice/rest/server.php'):
            self.api_url = f"{self.base_url}/webservice/rest/server.php"
        else:
            self.api_url = self.base_url
            
        self.token = moodle_token

    async def _call(self, function: str, params: dict = None):
        if params is None:
            params = {}
            
        params.update({
            "wstoken": self.token,
            "wsfunction": function,
            "moodlewsrestformat": "json"
        })
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, data=params)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict) and data.get('exception'):
                    logger.error(f"Moodle API Exception: {data.get('message')}")
                    return None
                    
                return data
            except Exception as e:
                logger.error(f"Moodle API Error: {str(e)}")
                return None

    async def get_site_info(self):
        """Get site info and user details."""
        return await self._call("core_webservice_get_site_info")

    async def get_courses(self):
        """Get courses the user is enrolled in."""
        site_info = await self.get_site_info()
        if not site_info:
            return []
            
        user_id = site_info.get('userid')
        return await self._call("core_enrol_get_users_courses", {"userid": user_id})

    async def get_course_contents(self, course_id: int):
        """Get sections and modules for a specific course."""
        return await self._call("core_course_get_contents", {"courseid": course_id})
