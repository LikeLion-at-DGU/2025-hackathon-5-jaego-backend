from django.db import models

class Product(models.Model):
    # 판매자 - 가게 1:1 관계 
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey('categories.Category', on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/', null=False, blank=False)
    discount_price = models.PositiveIntegerField()
    discount_rate = models.PositiveIntegerField(null=True, blank=True)
    stock = models.PositiveIntegerField()
    expiration_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.id}] {self.name} ({self.is_active})"


class Wishlist(models.Model):
    consumer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        unique_together = ('consumer', 'product')

    def __str__(self):
        return f"[{self.id}] {self.consumer.email} -> {self.product.name}"
