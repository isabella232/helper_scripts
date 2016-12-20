Валидатор наличия в QMS слоёв из набора OSMLAB



Первая половина скрипта для импорта слоёв из osmlab в Quick map services. Этот скрипт генерирует таблицу со слоями, что бы их скопировать вручную в Quick map servives
Потом обнаружили, что у QMS нет API импорта и отложили.

Он умеет:
1. Брать из файла список слоёв в osmlab. Этот файл imagery.json нужно скачать в репозитории osmlab
2. Выкачивать из REST API QMS данные по всем слоям, включая их адреса, и записывать в файл (функция downloadqms)
3. Генерировать таблицу в csv: там будет список слоёв из osmlab, и для каждого слоя по возможности похожие слои, которые уже есть в qms.
    Сравнение по домену и субдомену адреса: из обоих адресов выбирается строка например "openstreetmap.fr"


Нужно учитывать:
    в osmlab пишется {zoom} а в qms {z}
    в osmlab пишется {switch:a,b,c,d}, а в qms такой конструкции нету, и поэтому непонятнок как пишется


https://osmlab.github.io/editor-layer-index/ - сборник слоёв для обрисовки в Openstreetmap
Список слоёв хранится в файле https://github.com/osmlab/editor-layer-index/blob/gh-pages/imagery.json

# Использование

1. git clone
2. Скачать и положить сюда https://github.com/osmlab/editor-layer-index/blob/gh-pages/imagery.json
3. python run.py