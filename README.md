# TurKıyas

1. **Python 3.12+** ve [Ollama](https://ollama.com/download) kurun. Ek Python paketi gerekmez.
2. Depoyu indirin veya `dist/TurKiyas_Source.zip` dosyasını tamamen çıkarın. Terminali `tour_compare.py` dosyasının bulunduğu klasörde açın.
3. Ollama çalışırken modeli indirin (yaklaşık 2,5 GB):

```powershell
ollama pull qwen3:4b
```

Ollama hizmeti çalışmıyorsa ayrı bir terminalde `ollama serve` komutunu çalıştırıp açık bırakın.

4. Uygulamayı başlatın:

```powershell
python tour_compare.py
```

Windows'ta `run.cmd` dosyası da kullanılabilir. İlk yanıt model yüklenirken gecikebilir.

`Siz >` istemine mesajınızı yazıp Enter'a basın. Örnek:

```text
/liste
T01 ve T02 turlarını fiyat ve kahvaltı açısından karşılaştır.
/cikis
```

Model indirmeden anahtar kelime modunu denemek için:

```powershell
python tour_compare.py --backend rules
```
