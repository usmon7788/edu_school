with open('templates/feed/feed.html', 'r', encoding='utf-8') as f:
    content = f.read()

video_js = """

// ===== Video va Rasm yuklash funksiyalari =====
function triggerImageUpload() {
    document.getElementById('postVideoInput').value = '';
    document.getElementById('videoPreviewContainer').classList.add('d-none');
    document.getElementById('postImageInput').click();
}
function triggerVideoUpload() {
    document.getElementById('postImageInput').value = '';
    document.getElementById('imagePreviewContainer').classList.add('d-none');
    document.getElementById('postVideoInput').click();
}
document.addEventListener('DOMContentLoaded', function() {
    var imgInput = document.getElementById('postImageInput');
    if (imgInput) {
        imgInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('imagePreviewImg').src = e.target.result;
                    document.getElementById('imagePreviewFilename').innerHTML = '<i class="fa-solid fa-image me-1"></i>' + imgInput.files[0].name;
                    document.getElementById('imagePreviewContainer').classList.remove('d-none');
                    document.getElementById('composerDropzone').classList.add('d-none');
                    document.getElementById('videoPreviewContainer').classList.add('d-none');
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    var vidInput = document.getElementById('postVideoInput');
    if (vidInput) {
        vidInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                var url = URL.createObjectURL(this.files[0]);
                document.getElementById('videoPreviewEl').src = url;
                document.getElementById('videoPreviewFilename').innerHTML = '<i class="fa-solid fa-video me-1"></i>' + this.files[0].name;
                document.getElementById('videoPreviewContainer').classList.remove('d-none');
                document.getElementById('composerDropzone').classList.add('d-none');
                document.getElementById('imagePreviewContainer').classList.add('d-none');
            }
        });
    }
    var removeImgBtn = document.getElementById('removeImageBtn');
    if (removeImgBtn) {
        removeImgBtn.addEventListener('click', function() {
            document.getElementById('postImageInput').value = '';
            document.getElementById('imagePreviewContainer').classList.add('d-none');
            document.getElementById('composerDropzone').classList.remove('d-none');
        });
    }
    var removeVidBtn = document.getElementById('removeVideoBtn');
    if (removeVidBtn) {
        removeVidBtn.addEventListener('click', function() {
            document.getElementById('postVideoInput').value = '';
            document.getElementById('videoPreviewContainer').classList.add('d-none');
            document.getElementById('composerDropzone').classList.remove('d-none');
        });
    }
});
"""

idx = content.rfind('</script>')
if idx != -1:
    content = content[:idx] + video_js + '</script>' + content[idx+9:]
    with open('templates/feed/feed.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - video JS added')
else:
    print('NOT FOUND')
