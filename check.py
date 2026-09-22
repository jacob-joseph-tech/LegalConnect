import google.generativeai as genai

genai.configure(api_key="AIzaSyDYHQjdy5Wq_v0_PogoEHBv1K2m0INAqIM")

for m in genai.list_models():
    print(m.name)