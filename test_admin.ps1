$base = "http://127.0.0.1:8000"

function Kirish([string]$email, [string]$parol) {
    $t = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -Body @{ username = $email; password = $parol }
    return @{ Authorization = "Bearer $($t.access_token)" }
}
function YaratUser([string]$email, [string]$parol) {
    try { $null = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType "application/json" -Body (@{ email = $email; password = $parol } | ConvertTo-Json) } catch { }
}
function Royxat([string]$url, $sarlavha) {
    $r = Invoke-RestMethod -Uri "$base$url" -Headers $sarlavha
    return @($r | ForEach-Object { $_ })
}
function Tekshir([string]$nom, [int[]]$kutilgan, [scriptblock]$amal) {
    $kod = 200   # 200/201/204 shu yerda 200 deb olinadi
    try { $null = & $amal } catch { $kod = [int]$_.Exception.Response.StatusCode }
    $belgi = if ($kutilgan -contains $kod) { "OK  " } else { "XATO" }
    Write-Host "$belgi  $nom  (kutilgan: $($kutilgan -join '/'), chiqdi: $kod)"
}
function Qiymat([string]$nom, $haqiqiy, $kutilgan) {
    $belgi = if ($haqiqiy -eq $kutilgan) { "OK  " } else { "XATO" }
    Write-Host "$belgi  $nom  (kutilgan: $kutilgan, chiqdi: $haqiqiy)"
}
# Test bazasida SQL bajarish (SQLAlchemy orqali, parol so'ramaydi)
function BazaBuyrugi([string]$sql, [int]$id) {
    $kod = @"
from sqlalchemy import text
from app.database import engine
with engine.begin() as c:
    c.execute(text("$sql"), {"id": $id})
"@
    $kod | python -
}

Write-Host "--- 0) Tayyorgarlik ---"
BazaBuyrugi "DELETE FROM rentals WHERE id > :id" 0
YaratUser "customer1@example.com" "Parol12345"
YaratUser "customer2@example.com" "Parol12345"
$adminH = Kirish "admin@gmail.com" "12345678"
$aH = Kirish "customer1@example.com" "Parol12345"
$bH = Kirish "customer2@example.com" "Parol12345"

# Kamera: yo'q bo'lsa yaratiladi, narxi 100000 qilinadi
$cam = @{ name = "Canon EOS R6"; description = "Professional kamera"; category = "camera"; inventory_code = "CAM-001"; daily_rate = 100000 } | ConvertTo-Json
try { $null = Invoke-RestMethod -Method Post -Uri "$base/equipment" -Headers $adminH -ContentType "application/json" -Body $cam } catch { }
$camId = [int](Royxat "/equipment?search=canon" $adminH | Select-Object -First 1).id
$null = Invoke-RestMethod -Method Patch -Uri "$base/equipment/$camId" -Headers $adminH -ContentType "application/json" -Body (@{ daily_rate = 100000 } | ConvertTo-Json)
Write-Host "Kamera id = $camId"

Write-Host "--- 1) Customer A kamerani 3 kunga oladi ---"
$ijara = Invoke-RestMethod -Method Post -Uri "$base/rentals" -Headers $aH -ContentType "application/json" -Body (@{ equipment_id = $camId; days = 3 } | ConvertTo-Json)
$ijaraId = [int]$ijara.id
Qiymat "total_price = 300000" ([decimal]$ijara.total_price) 300000
Tekshir "Customer B ayni kamerani olmoqchi" 409 { Invoke-RestMethod -Method Post -Uri "$base/rentals" -Headers $bH -ContentType "application/json" -Body (@{ equipment_id = $camId; days = 1 } | ConvertTo-Json) }

Write-Host "--- 2) Ruxsatlar ---"
Tekshir "Customer: faol ijaralar" 403 { Invoke-RestMethod -Uri "$base/admin/rentals/active" -Headers $aH }
Tekshir "Customer: muddati o'tganlar" 403 { Invoke-RestMethod -Uri "$base/admin/rentals/overdue" -Headers $aH }
Tekshir "Customer: qaytarishni tasdiqlash" 403 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$ijaraId/return" -Headers $aH }
Tekshir "Tokensiz: faol ijaralar" 401 { Invoke-RestMethod -Uri "$base/admin/rentals/active" }
Tekshir "Tokensiz: qaytarish" 401 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$ijaraId/return" }

Write-Host "--- 3) Admin faol va muddati o'tgan ijaralarni ko'radi ---"
Qiymat "Faol ijaralar soni" @(Royxat "/admin/rentals/active" $adminH).Count 1
Qiymat "Muddati o'tganlar soni (hali yo'q)" @(Royxat "/admin/rentals/overdue" $adminH).Count 0

# Ijarani sun'iy ravishda muddati o'tgan qilamiz: 4 kun oldin boshlangan, 1 kun oldin tugagan
BazaBuyrugi "UPDATE rentals SET start_at = now() - interval '4 days', due_at = now() - interval '1 day' WHERE id = :id" $ijaraId
$muddat = @(Royxat "/admin/rentals/overdue" $adminH)
Qiymat "Muddati o'tganlar soni" $muddat.Count 1
Qiymat "Muddati o'tgan ijara id si" ([int]$muddat[0].id) $ijaraId
Qiymat "is_overdue = True" $muddat[0].is_overdue $true
Qiymat "Faol ro'yxatda ham turibdi" @(Royxat "/admin/rentals/active" $adminH).Count 1

Write-Host "--- 4) Qaytarishni tasdiqlash ---"
$qaytgan = Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$ijaraId/return" -Headers $adminH
Qiymat "returned_at to'ldirildi" ($null -ne $qaytgan.returned_at) $true
Qiymat "is_overdue = False (qaytarilgan)" $qaytgan.is_overdue $false
Tekshir "Ikkinchi marta qaytarish" 409 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$ijaraId/return" -Headers $adminH }
Tekshir "Mavjud bo'lmagan ijara" 404 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/999999/return" -Headers $adminH }

Write-Host "--- 5) Qaytarilgandan keyin ---"
Qiymat "Faol ijaralar soni" @(Royxat "/admin/rentals/active" $adminH).Count 0
Qiymat "Muddati o'tganlar soni" @(Royxat "/admin/rentals/overdue" $adminH).Count 0
Qiymat "Kamera available ro'yxatida yana bor" @(Royxat "/equipment/available" $bH | Where-Object { $_.id -eq $camId }).Count 1
$mening = @(Royxat "/rentals/my" $aH)
Qiymat "A ning tarixida returned_at bor" ($null -ne $mening[0].returned_at) $true
Tekshir "B, A ning ijarasini ko'rmoqchi" 404 { Invoke-RestMethod -Uri "$base/rentals/$ijaraId" -Headers $bH }

Write-Host "--- 6) Qayta ijaraga olish ---"
Tekshir "B kamerani endi oladi" 200 { Invoke-RestMethod -Method Post -Uri "$base/rentals" -Headers $bH -ContentType "application/json" -Body (@{ equipment_id = $camId; days = 1 } | ConvertTo-Json) }
$bIjara = @(Royxat "/admin/rentals/active" $adminH)[0]
Tekshir "Admin B ning ijarasini qaytaradi" 200 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$($bIjara.id)/return" -Headers $adminH }

Write-Host "--- 7) Parallel ijara (ikki alohida jarayon) ---"
$govda = @{ equipment_id = $camId; days = 1 } | ConvertTo-Json
$ishlar = @($aH, $bH) | ForEach-Object {
    Start-Job -ScriptBlock {
        param($base, $h, $body)
        try { $null = Invoke-RestMethod -Method Post -Uri "$base/rentals" -Headers $h -ContentType "application/json" -Body $body; 201 }
        catch { [int]$_.Exception.Response.StatusCode }
    } -ArgumentList $base, $_, $govda
}
$natija = @($ishlar | Wait-Job | Receive-Job | Sort-Object)
$ishlar | Remove-Job
Qiymat "Natijalar: bittasi 201, bittasi 409" ($natija -join ",") "201,409"
Qiymat "Faqat bitta faol ijara bor" @(Royxat "/admin/rentals/active" $adminH).Count 1

# Tozalash: kamerani bo'shatish
$qoldi = @(Royxat "/admin/rentals/active" $adminH)[0]
Tekshir "Tozalash: qolgan ijarani qaytarish" 200 { Invoke-RestMethod -Method Post -Uri "$base/admin/rentals/$($qoldi.id)/return" -Headers $adminH }