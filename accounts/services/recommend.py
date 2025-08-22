# import os
# from openai import OpenAI
# from ..models import KeywordCache
# from django.utils import timezone

# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# def extract_keywords(product_name: str, category_name: str) -> list[str]:
#     prompt = f"""
#     상품명: {product_name}
#     카테고리: {category_name}

#     위 상품을 가장 잘 나타내는 '상품군/재료/종류' 중심의 명사 키워드만 3개 뽑아줘.
#     쉼표(,)로 구분해서 반환해.
#     예시: 치킨, 튀김, 닭고기
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "너는 상품명을 분석해 핵심 키워드를 뽑아내는 보조 도우미야."},
#             {"role": "user", "content": prompt},
#         ],
#         max_tokens=50,
#     )

#     keywords_str = response.choices[0].message.content.strip()
#     keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
#     return keywords

# def get_keywords_from_gpt_or_cache(product_name, category_name):
#     try:
#         cache = KeywordCache.objects.get(
#             product_name=product_name,
#             category_name=category_name
#         )
#         return cache.keywords
#     except KeywordCache.DoesNotExist:
#         # GPT 호출
#         keywords = extract_keywords(product_name, category_name)

#         # 캐싱 저장
#         KeywordCache.objects.create(
#             product_name=product_name,
#             category_name=category_name,
#             keywords=keywords
#         )
#         return keywords
