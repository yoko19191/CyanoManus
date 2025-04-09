from logging import logger

def create_logged_tool(tool_cls):
    """Create a logged version of a tool class."""
    
    class LoggedTool(tool_cls):
        def _run(self, *args, **kwargs):
            logger.info(f"Running {self.name} with args: {args}, kwargs: {kwargs}")
            try:
                result = super()._run(*args, **kwargs)
                logger.debug(f"{self.name} result: {result[:100]}..." if len(str(result)) > 100 else result)
                return result
            except Exception as e:
                logger.error(f"Error in {self.name}: {e}")
                raise
                
    return LoggedTool