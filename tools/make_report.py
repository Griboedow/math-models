"""Generate figures and the Russian result note from saved numerical outputs."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'results/scenarios.json').read_text(encoding='utf-8'))
sens=json.loads((ROOT/'results/sensitivity.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.facecolor':'#fffdf9','figure.facecolor':'#f4f2eb','axes.labelcolor':'#25352e','text.color':'#25352e','grid.color':'#d8e1d7'})
def get(ball,motion,setup='desk_side',stand='pitaya_v08'):
    return next(x for x in rows if x['case']==dict(stand=stand,ball=ball,motion=motion,setup=setup))
fig,axs=plt.subplots(2,2,figsize=(12,6),sharex=True)
for col,ba in enumerate(['full','nearly_empty']):
    for mo,color in [('knitting','#236b50'),('crochet','#ba2e71')]:
        r=get(ba,mo);t=[x['t_s'] for x in r['trace']]
        axs[0,col].plot(t,[x['tension_N'] for x in r['trace']],color=color,label='Спицы' if mo=='knitting' else 'Крючок',lw=1.8)
        axs[1,col].plot(t,[x['slack_m']*1000 for x in r['trace']],color=color,lw=1.8)
    axs[0,col].set_title('Полный · 100 г' if ba=='full' else 'Почти пустой · 10 г (условное сцепление)')
    axs[1,col].set_xlabel('Время, с')
    for ax in axs[:,col]:ax.grid(alpha=.7)
axs[0,0].set_ylabel('Натяжение, Н');axs[1,0].set_ylabel('Условный избыток выдачи, мм');axs[0,0].legend(frameon=False)
fig.suptitle('PITAYA · подставка сбоку на столе',fontsize=17)
fig.text(.05,.015,'Сценарные параметры, без физических измерений. Справа допущение сцепления нарушается; кривые не предсказывают реальное скольжение.',fontsize=9)
fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(ROOT/'docs/tension.png',dpi=150);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(11,4.4))
for ba,col,label in [('full','#236b50','Полный'),('nearly_empty','#ba2e71','Почти пустой')]:
    points=[x for x in sens if x['sweep']=='bearing_and_feet' and x['ball_preset']==ba and x['motion_preset']=='knitting' and x['foot_mu']==.45]
    axs[0].plot([x['start_torque_mNm'] for x in points],[x['start_N'] for x in points],'o-',color=col,label=label)
    setups=['desk_side','front','far_side','high_table','floor']
    axs[1].plot(range(5),[get(ba,'knitting',p)['summary']['static_limits']['critical_snag_N'] for p in setups],'o-',color=col,label=label)
axs[0].set(xlabel='Пусковой момент узла, мН·м',ylabel='Пусковое натяжение, Н',title='Маленький клубок: меньше рабочее плечо')
axs[1].set(xticks=range(5),xticklabels=['Сбоку','Спереди','Далеко','Руки ниже','Пол'],ylabel='Статический порог зацепа, Н',title='Первый предел сдвига / наклона / отрыва')
for ax in axs:ax.grid(alpha=.7);ax.legend(frameon=False)
fig.tight_layout();fig.savefig(ROOT/'docs/sensitivity.png',dpi=150);plt.close(fig)

lines=['# Результаты расчёта PITAYA','',
'Все числа ниже рассчитаны при сценарных, ещё не измеренных свойствах пряжи и подставки. Размеры ножек и площадки взяты из CAD. Это ориентиры для пробы, не аттестация изделия.','',
'## Сбоку на столе','',
'До рабочей руки 40 см по горизонтали, рука на 20 см выше поверхности под ножками. Подставка 230 г; полный клубок 100 г, почти пустой 10 г.','',
'| Клубок | Подача | Пуск, Н | Пик связанной модели, Н | Порог зацепа, Н | Сцепление весь прогон |',
'|---|---|---:|---:|---:|---|']
for ba in ['full','nearly_empty']:
    for mo in ['knitting','crochet']:
        x=get(ba,mo)['summary'];lines.append(f"| {'Полный' if ba=='full' else 'Почти пустой'} | {'Спицы' if mo=='knitting' else 'Крючок'} | {x['static_limits']['start_tension_N']:.3f} | {x['peak_tension_N']:.3f} | {x['static_limits']['critical_snag_N']:.2f} | {'да, при допущениях' if x['hypotheses_valid_for_entire_run'] else 'нет; пик условный'} |")
lines += ['',
'У почти пустого клубка в исходном сценарии не хватает сцепления с площадкой. Поэтому его динамические пики нельзя выдавать за реальные силы. Плотность посадки на палочку особенно важна; отдельный анализ `spindle_grip` показывает влияние дополнительного удерживающего момента.','',
'![Натяжение](tension.png)','','## Что следует из сравнения','',
'- Малый радиус клубка повышает пусковое натяжение при том же сопротивлении узла. Потеря массы не гарантирует лёгкой подачи.',
'- Резкие импульсы выбранного сценария крючка дают больший разгон и выбег. Это эффект заданного ритма, не обязательное свойство вязания крючком.',
'- При стандартных параметрах расчёт не выявил сдвига или наклона PITAYA в обычной подаче. Порог около одного ньютона относится к зацепу и не является большим запасом против сильного рывка рукой.',
'- При руках ниже высокой подставки низкий выход нити из остатка клубка может пересекать край. Изменение формы листьев не устраняет эту причину: важнее взаимная высота руки и подставки.',
'- При крутой тяге вверх уменьшается рабочее плечо и прижим клубка. Возможен другой режим схода нити, который модель не описывает.',
'- Более широкая опора улучшает предел наклона, но не исправляет скользкие ножки. Для сравнения меняйте реальную геометрию контакта, а не диаметр декора.','',
'![Чувствительность](sensitivity.png)','','## Состав проверок','',
f'- {len(rows)} сценариев подставка × клубок × ритм × положение.',
f'- {len(sens)} случаев чувствительности: сопротивление узла, трение ножек, упругость нити, сход слоёв и посадка на палочку.',
'- 864 геометрических проверки пути: два вида листьев, два клубка, три положения, три высоты выхода и 24 азимута. Это сетка проверок, не статистика вероятности.',
'- Аналитические тесты равновесия, касательной, инвариантности при повороте, интеграла подачи, ошибок конфигурации и сходимости по времени.','',
'Для практической пробы сначала проверить низкое сопротивление вращению и посадку остатка клубка. Обычный столик рядом с рукой — разумная исходная конфигурация для испытания. После печати подставить несколько измерений по [инструкции](calibration.md).','']
(ROOT/'docs/results.md').write_text('\n'.join(lines),encoding='utf-8')
print('Figures and result note generated from saved outputs')
