def send_response(data, status_code=200, message="", error=""):
    return {"status": status_code, "data": data, "message": message, "error": error}
