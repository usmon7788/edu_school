
# 1. Login page - quick chips olib tashlash
login_html = """{% extends 'base.html' %}

{% block title %}{{ t.login }} - {{ t.school_portal }}{% endblock %}

{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-md-7 col-lg-5 col-xl-4">
            <div class="card card-modern p-4 p-md-5 shadow-lg border-0">
                <div class="text-center mb-4">
                    <div class="brand-badge mb-3 mx-auto" style="width:62px;height:62px;font-size:1.85rem;border-radius:18px;">
                        <i class="fa-solid fa-graduation-cap"></i>
                    </div>
                    <h2 class="fw-bold mb-1">{{ t.welcome }}</h2>
                    <p class="text-muted small">Tizimga kirish uchun login va parolingizni kiriting</p>
                </div>

                <form method="post" novalidate>
                    {% csrf_token %}
                    <div class="mb-3">
                        <label class="form-label fw-semibold text-secondary small">{{ t.username }} (Login)</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="fa-solid fa-user"></i></span>
                            {{ form.username }}
                        </div>
                    </div>
                    <div class="mb-4">
                        <label class="form-label fw-semibold text-secondary small">{{ t.password }}</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="fa-solid fa-lock"></i></span>
                            {{ form.password }}
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary-custom w-100 py-3 fs-6 mb-3">
                        <i class="fa-solid fa-arrow-right-to-bracket me-2"></i> {{ t.login }}
                    </button>
                    <div class="text-center">
                        <span class="text-muted small">Akkauntingiz yo'qmi?</span>
                        <a href="{% url 'register' %}" class="fw-bold text-primary text-decoration-none ms-1 small">
                            {{ t.register }}
                        </a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

with open("templates/auth/login.html", "w", encoding="utf-8") as f:
    f.write(login_html)
print("login.html OK")
