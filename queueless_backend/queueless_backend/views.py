from django.http import HttpResponse


def landing_page(request):
    """
    Returns a premium landing page for the QueueLess Backend.
    """
    font_link = (
        "https://fonts.googleapis.com/css2?"
        "family=Outfit:wght@300;400;600&display=swap"
    )

    frontend_url = "https://queue-less-ph.vercel.app"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QueueLess | API Engine</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="{font_link}" rel="stylesheet">
        <style>
            :root {{
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --bg: #0f172a;
                --card-bg: rgba(30, 41, 59, 0.7);
                --text: #f8fafc;
                --text-muted: #94a3b8;
            }}
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                background-image:
                    radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px,
                                    transparent 50%),
                    radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.1) 0px,
                                    transparent 50%);
                color: var(--text);
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            .container {{
                max-width: 600px;
                width: 90%;
                text-align: center;
                padding: 3rem;
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                animation: fadeIn 0.8s ease-out;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .logo {{
                font-size: 3rem;
                font-weight: 600;
                margin-bottom: 1rem;
                background: linear-gradient(to right, #818cf8, #c084fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: -0.02em;
            }}
            h1 {{
                font-size: 1.5rem;
                font-weight: 400;
                margin-bottom: 1.5rem;
                color: var(--text-muted);
            }}
            p {{
                line-height: 1.6;
                margin-bottom: 2.5rem;
                color: var(--text-muted);
                font-size: 1.1rem;
            }}
            .btn {{
                display: inline-block;
                background-color: var(--primary);
                color: white;
                padding: 1rem 2.5rem;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                            0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }}
            .btn:hover {{
                background-color: var(--primary-hover);
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
            }}
            .badge {{
                display: inline-block;
                padding: 0.25rem 0.75rem;
                background: rgba(99, 102, 241, 0.1);
                border: 1px solid rgba(99, 102, 241, 0.2);
                border-radius: 100px;
                color: #818cf8;
                font-size: 0.875rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="badge">v2.0 Beta</div>
            <div class="logo">QueueLess</div>
            <h1>API Core Engine</h1>
            <p>
                The heavy lifting happens here. This backend manages
                real-time queue states, synchronizes notifications,
                and powers the entire QueueLess ecosystem.
            </p>
            <a href="{frontend_url}"
               class="btn">Launch Frontend Application</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)
