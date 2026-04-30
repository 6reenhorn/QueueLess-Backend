from django.http import HttpResponse


def landing_page(request):
    """
    Returns a harmonized, premium landing page for the QueueLess Backend.
    """
    font_link = (
        "https://fonts.googleapis.com/css2?"
        "family=Outfit:wght@300;400;500;600;700&display=swap"
    )

    frontend_url = "https://queueless-ph.vercel.app"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QueueLess | API Core Engine</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="{font_link}" rel="stylesheet">
        <style>
            :root {{
                --navy: #0f172a;
                --primary: #2563eb;
                --primary-light: #eff6ff;
                --text: #1e293b;
                --text-muted: #64748b;
                --bg: #ffffff;
                --gradient-bg: radial-gradient(
                    circle at top right, #f0f9ff 0%, #ffffff 100%
                );
            }}
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Outfit', sans-serif;
                background: var(--bg);
                background-image: var(--gradient-bg);
                color: var(--text);
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            .nav {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                padding: 2rem;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .logo-container {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: var(--navy);
                text-decoration: none;
            }}
            .logo-icon {{
                width: 32px;
                height: 32px;
                background: var(--navy);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .logo-text {{
                font-size: 1.5rem;
                font-weight: 700;
                letter-spacing: -0.02em;
            }}
            .hero {{
                text-align: center;
                max-width: 800px;
                padding: 2rem;
                animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
            }}
            @keyframes slideUp {{
                from {{ opacity: 0; transform: translateY(30px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .badge-wrapper {{
                margin-bottom: 1.5rem;
            }}
            .badge {{
                display: inline-block;
                padding: 0.5rem 1.25rem;
                background: var(--primary-light);
                color: var(--primary);
                border-radius: 100px;
                font-size: 0.875rem;
                font-weight: 600;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                border: 1px solid rgba(37, 99, 235, 0.1);
            }}
            h1 {{
                font-size: clamp(2.5rem, 8vw, 4rem);
                font-weight: 700;
                line-height: 1.1;
                margin-bottom: 1.5rem;
                color: var(--navy);
                letter-spacing: -0.03em;
            }}
            h1 span {{
                color: var(--primary);
            }}
            p {{
                font-size: 1.25rem;
                line-height: 1.6;
                color: var(--text-muted);
                margin-bottom: 3rem;
                max-width: 600px;
                margin-left: auto;
                margin-right: auto;
            }}
            .cta-group {{
                display: flex;
                gap: 1rem;
                justify-content: center;
                align-items: center;
            }}
            .btn {{
                padding: 1rem 2rem;
                border-radius: 12px;
                font-size: 1.125rem;
                font-weight: 600;
                text-decoration: none;
                transition: all 0.2s ease;
            }}
            .btn-primary {{
                background: var(--navy);
                color: white;
                box-shadow: 0 4px 14px 0 rgba(15, 23, 42, 0.2);
            }}
            .btn-primary:hover {{
                background: #1e293b;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(15, 23, 42, 0.3);
            }}
            .btn-secondary {{
                background: white;
                color: var(--text);
                border: 1px solid #e2e8f0;
            }}
            .btn-secondary:hover {{
                background: #f8fafc;
                border-color: #cbd5e1;
            }}
            .stats {{
                margin-top: 5rem;
                display: flex;
                gap: 4rem;
                justify-content: center;
                border-top: 1px solid #f1f5f9;
                padding-top: 3rem;
            }}
            .stat-item {{
                text-align: left;
            }}
            .stat-value {{
                font-size: 2rem;
                font-weight: 700;
                color: var(--navy);
                display: block;
            }}
            .stat-label {{
                font-size: 0.875rem;
                color: var(--text-muted);
                font-weight: 500;
            }}
            .abstract-shapes {{
                position: absolute;
                z-index: -1;
                width: 100%;
                height: 100vh;
                top: 0;
                left: 0;
                pointer-events: none;
                overflow: hidden;
            }}
            .shape {{
                position: absolute;
                background: radial-gradient(
                    circle, rgba(37, 99, 235, 0.05) 0%, transparent 70%
                );
                border-radius: 50%;
            }}
        </style>
    </head>
    <body>
        <div class="abstract-shapes">
            <div class="shape" style="
                width: 600px; height: 600px; top: -200px; right: -100px;
            "></div>
            <div class="shape" style="
                width: 400px; height: 400px; bottom: -100px; left: -100px;
            "></div>
        </div>

        <nav class="nav">
            <a href="/" class="logo-container">
                <div class="logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24"
                         fill="none" stroke="currentColor" stroke-width="2.5"
                         stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
                <span class="logo-text">QueueLess</span>
            </a>
        </nav>

        <main class="hero">
            <div class="badge-wrapper">
                <span class="badge">API Engine v1.0 Beta</span>
            </div>
            <h1>Your API Core, <span>Synchronized.</span></h1>
            <p>
                Powers real-time queue states, smart notifications, and seamless
                integration for the QueueLess ecosystem.
            </p>
            <div class="cta-group">
                <a href="{frontend_url}" class="btn btn-primary">Launch Frontend</a>
                <a href="/admin/" class="btn btn-secondary">Admin Console</a>
            </div>

            <div class="stats">
                <div class="stat-item">
                    <span class="stat-value">99.9%</span>
                    <span class="stat-label">Uptime SLA</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">&lt;50ms</span>
                    <span class="stat-label">Avg Response</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">Real-time</span>
                    <span class="stat-label">Engine Status</span>
                </div>
            </div>
        </main>
    </body>
    </html>
    """
    return HttpResponse(html_content)
