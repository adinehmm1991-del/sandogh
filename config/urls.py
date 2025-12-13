from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ابزارهای Swagger
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# تنظیمات ظاهری Swagger
schema_view = get_schema_view(
   openapi.Info(
      title="مستندات صندوق ثنای حق",
      default_version='v1',
      description="لیست تمام APIهای مورد نیاز برای سایت و اپلیکیشن",
      contact=openapi.Contact(email="admin@sanayehagh.ir"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/accounting/', include('accounting.urls')),
    
    # آدرس ورود به صفحه مستندات
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

# نمایش عکس‌ها
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)