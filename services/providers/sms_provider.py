class SMSProvider:

    def send_otp(self, phone_number: str, otp: str):
        print(f"OTP for {phone_number}: {otp}")
