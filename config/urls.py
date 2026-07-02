from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
import os
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
    # 1. پنل ادمین و APIها
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/accounting/', include('accounting.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    # فایل‌های اصلی ری‌اکت
    re_path(r'^(?P<path>(?:logo\.png|manifest\.json|vite\.svg))$', serve, 
            {'document_root': os.path.join(settings.BASE_DIR, 'frontend/dist')}),
            
    # ---> این خط جدید اضافه شد تا کدهای جدید جاوااسکریپت لود شوند <---
    re_path(r'^assets/(?P<path>.*)$', serve, 
            {'document_root': os.path.join(settings.BASE_DIR, 'frontend/dist/assets')}),
]

# 2. تنظیمات فایل‌های استاتیک و مدیا
# این موارد حتماً باید قبل از catch-all نهایی ریکت اضافه شوند
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 3. شاه‌کلید حل مشکل رفرش (SPA Catch-all)
# این خط حتماً باید آخرین مسیر در کل پروژه باشد
urlpatterns += [
    re_path(r'^(?!api|admin|media|static|swagger).*$', TemplateView.as_view(template_name='index.html')),
]