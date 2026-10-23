
$base = "http://127.0.0.1:8000"

function Kirish($email, $password) {
    $form = @{
        username = $email
        password = $password
    }

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$base/auth/login" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body $form

    return @{
        Authorization = "Bearer $($response.access_token)"
    }
}

# Server ishlayotganini tekshirish
try {
    $response = Invoke-RestMethod -Uri "$base/openapi.json"
    Write-Host "API ishlayapti!" -ForegroundColor Green
}
catch {
    Write-Host "API serveriga ulanib bo'lmadi." -ForegroundColor Red
    Write-Host "Avval uvicorn serverini ishga tushiring."
    return
}

# Admin hisobiga kirish
$adminH = Kirish "admin@gmail.com" "12345678"

Write-Host "Admin login muvaffaqiyatli!" -ForegroundColor Green
