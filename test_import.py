import traceback
try:
    import voice_ext_endpoints
    print("SUCCESS")
except Exception as e:
    print(traceback.format_exc())
