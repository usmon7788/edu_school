with open('apps/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "        'sound_choices': UserSettings.SOUND_CHOICES,\n        'theme_choices': UserSettings.THEME_CHOICES,\n    }\n    return render(request, 'settings/settings.html', context)"

new = "        'sound_choices': UserSettings.SOUND_CHOICES,\n        'theme_choices': UserSettings.THEME_CHOICES,\n        'languages': [\n            {'code': 'uz', 'name': \"O'zbekcha\", 'flag': '\U0001f1fa\U0001f1ff'},\n            {'code': 'ru', 'name': 'Ruscha', 'flag': '\U0001f1f7\U0001f1fa'},\n            {'code': 'en', 'name': 'English', 'flag': '\U0001f1ec\U0001f1e7'},\n        ],\n    }\n    return render(request, 'settings/settings.html', context)"

if old in content:
    content = content.replace(old, new, 1)
    with open('apps/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    # Try CRLF
    old2 = "        'sound_choices': UserSettings.SOUND_CHOICES,\r\n        'theme_choices': UserSettings.THEME_CHOICES,\r\n    }\r\n    return render(request, 'settings/settings.html', context)"
    new2 = "        'sound_choices': UserSettings.SOUND_CHOICES,\r\n        'theme_choices': UserSettings.THEME_CHOICES,\r\n        'languages': [\r\n            {'code': 'uz', 'name': \"O'zbekcha\", 'flag': '\U0001f1fa\U0001f1ff'},\r\n            {'code': 'ru', 'name': 'Ruscha', 'flag': '\U0001f1f7\U0001f1fa'},\r\n            {'code': 'en', 'name': 'English', 'flag': '\U0001f1ec\U0001f1e7'},\r\n        ],\r\n    }\r\n    return render(request, 'settings/settings.html', context)"
    if old2 in content:
        content = content.replace(old2, new2, 1)
        with open('apps/views.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK CRLF')
    else:
        print('FAILED - showing snippet:')
        idx = content.find('sound_choices')
        print(repr(content[idx-100:idx+300]))
