<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import { workApi } from '../api'
import type { WorkActionName, WorkDetail } from '../types'

const props = defineProps<{ work: WorkDetail; disabled: boolean }>()
const emit = defineEmits<{ saved: [item: WorkDetail]; busy: [value: boolean]; editing: [value: boolean]; uncertain: [] }>()
const action = ref<WorkActionName | null>(null)
const saving = ref(false)
const message = ref('')
const start = ref('')
const deadline = ref('')
const expectedReturn = ref('')
const serverError = ref('')
const form = ref<HTMLFormElement | null>(null)
const prefix = 'work-actions-' + props.work.id
const errorKeys = ['action', 'scheduled_start_on', 'due_on', 'expected_return_on', 'message', 'row_version'] as const
const errors = reactive(Object.fromEntries(errorKeys.map(key => [key, ''])) as Record<typeof errorKeys[number], string>)
const locked = computed(() => props.disabled || saving.value)
const options: { value: WorkActionName; label: string; icon: string; tone: 'success' | 'danger' | 'brand' | 'neutral'; message?: string }[] = [
  { value: 'start', label: 'Iniciar', icon: 'pi pi-play', tone: 'success' },
  { value: 'resume', label: 'Retomar', icon: 'pi pi-play', tone: 'success' },
  { value: 'reopen', label: 'Reabrir demanda', icon: 'pi pi-replay', tone: 'brand', message: 'Motivo da reabertura' },
  { value: 'complete', label: 'Concluir', icon: 'pi pi-check', tone: 'success' },
  { value: 'cancel', label: 'Cancelar demanda', icon: 'pi pi-times', tone: 'danger', message: 'Justificativa do cancelamento' },
  { value: 'schedule', label: props.work.scheduled_start_on ? 'Alterar agendamento' : 'Agendar início', icon: 'pi pi-calendar-plus', tone: 'brand' },
  { value: 'cancel_schedule', label: 'Cancelar agendamento', icon: 'pi pi-calendar-times', tone: 'neutral' },
  { value: 'request_information', label: 'Solicitar mais informações', icon: 'pi pi-comment', tone: 'neutral', message: 'Informações necessárias' },
  { value: 'validate', label: 'Iniciar validação', icon: 'pi pi-verified', tone: 'brand', message: 'Orientações para a validação' },
  { value: 'pause', label: 'Pausar', icon: 'pi pi-pause', tone: 'neutral', message: 'Motivo da pausa' },
  { value: 'wait_third_party', label: 'Aguardar terceiros', icon: 'pi pi-users', tone: 'neutral', message: 'Pendências com terceiros' },
  { value: 'change_deadline', label: 'Alterar prazo', icon: 'pi pi-calendar', tone: 'brand', message: 'Justificativa do novo prazo' },
]
const available = computed(() => options.filter(option => props.work.available_actions.includes(option.value)))
const selected = computed(() => options.find(option => option.value === action.value))
const needsDeadline = computed(() => action.value !== null && ['start', 'schedule', 'change_deadline', 'reopen'].includes(action.value))
function today() {
  const parts = new Intl.DateTimeFormat('en', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  return ['year', 'month', 'day'].map(type => parts.find(part => part.type === type)?.value ?? '').join('-')
}
const earliestDeadline = computed(() => {
  const beginning = action.value === 'schedule' ? start.value : action.value === 'start' ? today()
    : props.work.started_on ?? props.work.scheduled_start_on ?? today()
  return beginning > today() ? beginning : today()
})
watch(saving, value => emit('busy', value), { flush: 'sync' })
watch(action, value => emit('editing', value !== null), { flush: 'sync' })

async function choose(value: WorkActionName) {
  if (locked.value || !props.work.available_actions.includes(value)) return
  action.value = value
  message.value = ''
  start.value = props.work.scheduled_start_on ?? ''
  deadline.value = props.work.due_on ?? ''
  expectedReturn.value = props.work.expected_return_on ?? ''
  serverError.value = ''
  errorKeys.forEach(key => { errors[key] = '' })
  await nextTick()
  document.getElementById(prefix + (value === 'schedule' ? '-start' : needsDeadline.value ? '-deadline' : selected.value?.message ? '-message' : '-confirm'))?.focus()
}
async function back() {
  if (locked.value) return
  const previous = action.value
  action.value = null
  await nextTick()
  document.getElementById(prefix + '-choose-' + previous)?.focus()
}
async function focusError() {
  await nextTick()
  const target = form.value?.querySelector<HTMLElement>('[aria-invalid="true"]') ?? document.getElementById(prefix + '-error')
  target?.focus()
}
async function submit() {
  if (locked.value || !action.value) return
  errorKeys.forEach(key => { errors[key] = '' })
  serverError.value = ''
  if (action.value === 'schedule' && (!start.value || start.value < today())) errors.scheduled_start_on = 'Selecione hoje ou uma data futura.'
  if (needsDeadline.value && (!deadline.value || deadline.value < earliestDeadline.value)) errors.due_on = 'Informe um prazo igual ou posterior a hoje e ao início.'
  if (action.value === 'pause' && (!expectedReturn.value || expectedReturn.value < today())) errors.expected_return_on = 'Informe hoje ou uma data futura para a previsão de retorno.'
  if (selected.value?.message && !message.value.trim()) errors.message = 'Preencha este campo para registrar a ação.'
  if (errorKeys.some(key => errors[key])) { await focusError(); return }
  saving.value = true
  let saved: WorkDetail | undefined
  try {
    saved = await workApi.action(props.work.id, { action: action.value, row_version: props.work.row_version,
      scheduled_start_on: action.value === 'schedule' ? start.value : null,
      due_on: needsDeadline.value ? deadline.value : null, expected_return_on: action.value === 'pause' ? expectedReturn.value : null,
      message: selected.value?.message ? message.value.trim() : null })
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível registrar a ação.'
    if (error instanceof ApiError) {
      Object.assign(errors, validationMessages(error.detail, errorKeys))
      if ([0, 401, 403, 409].includes(error.status) || error.status >= 500 || (error.status >= 200 && error.status < 300)) emit('uncertain')
    } else emit('uncertain')
  } finally { saving.value = false }
  if (saved) emit('saved', saved)
  else await focusError()
}
</script>

<template>
  <section :aria-labelledby="prefix + '-title'">
    <h5 :id="prefix + '-title'" class="text-xs font-semibold text-dj-muted">Ações da demanda</h5>
    <p v-if="!work.available_actions.length" class="mt-2 text-sm text-dj-muted">Não há ações disponíveis para esta situação.</p>
    <div v-else-if="!action" class="mt-2 flex flex-wrap gap-2" role="group" aria-label="Ações principais">
      <Button v-for="option in available" :id="prefix + '-choose-' + option.value" :key="option.value" type="button"
        :label="option.label" :icon="option.icon" :disabled="locked" :aria-pressed="action === option.value"
        :aria-controls="prefix + '-form'" class="demand-work-action justify-center rounded-lg" :class="'dj-tone-' + option.tone" @click="choose(option.value)" />
    </div>
    <form v-if="action && selected" :id="prefix + '-form'" ref="form" novalidate class="mt-3 space-y-3" @submit.prevent="submit">
      <h5 class="text-sm font-semibold">{{ selected.label }}</h5>
      <Message v-if="serverError" :id="prefix + '-error'" severity="error" tabindex="-1" role="alert">{{ serverError }}</Message>
      <Message v-if="errors.row_version || errors.action" severity="error">{{ errors.row_version || errors.action }}</Message>
      <p v-if="action === 'start'" class="text-sm text-dj-muted">O início será registrado com a data de hoje, no horário de Brasília.</p>
      <p v-if="action === 'schedule'" class="text-sm text-dj-muted">Defina o início e o prazo. A demanda será iniciada automaticamente na data agendada.</p>
      <p v-if="action === 'cancel_schedule'" class="text-sm text-dj-muted">O início agendado e seu prazo serão removidos. A demanda voltará para A fazer.</p>
      <p v-if="action === 'reopen'" class="text-sm text-dj-muted">Informe um novo prazo e o motivo. A demanda voltará para Em andamento, preservando o início original e o histórico.</p>
      <p v-if="action === 'resume'" class="text-sm text-dj-muted">A demanda voltará a ficar em andamento, mantendo o início e o prazo atuais.</p>
      <p v-if="action === 'complete'" class="text-sm text-dj-muted">Confirme a conclusão da demanda. O encerramento ficará registrado no histórico.</p>
      <div v-if="needsDeadline" class="grid gap-4 sm:grid-cols-2">
        <FormField v-if="action === 'schedule'" :id="prefix + '-start'" label="Data de início *" :error="errors.scheduled_start_on" v-slot="{ controlProps }">
          <InputText v-model="start" v-bind="controlProps" type="date" :min="today()" max="9999-12-31" required :disabled="locked" class="w-full" />
        </FormField>
        <FormField :id="prefix + '-deadline'" label="Prazo de entrega *" :error="errors.due_on" v-slot="{ controlProps }">
          <InputText v-model="deadline" v-bind="controlProps" type="date" :min="earliestDeadline" max="9999-12-31" required :disabled="locked" class="w-full" />
        </FormField>
      </div>
      <FormField v-if="action === 'pause'" :id="prefix + '-return'" label="Previsão de retorno *" :error="errors.expected_return_on" v-slot="{ controlProps }">
        <InputText v-model="expectedReturn" v-bind="controlProps" type="date" :min="today()" max="9999-12-31" required :disabled="locked" class="w-full" />
      </FormField>
      <FormField v-if="selected.message" :id="prefix + '-message'" :label="selected.message + ' *'" :error="errors.message" v-slot="{ controlProps }">
        <Textarea v-model="message" v-bind="controlProps" required :rows="3" :maxlength="4000" :disabled="locked" class="w-full" />
      </FormField>
      <p v-if="selected.message" class="text-xs leading-5 text-dj-muted">A mensagem ficará registrada no histórico da demanda.</p>
      <div class="flex flex-wrap gap-3">
        <Button :id="prefix + '-confirm'" type="submit" :label="'Confirmar: ' + selected.label.toLowerCase()" :loading="saving" :disabled="locked"
          class="demand-work-action" :class="'dj-tone-' + selected.tone" />
        <SecondaryButton type="button" label="Voltar" outlined :disabled="locked" @click="back" />
      </div>
    </form>
  </section>
</template>

<style scoped>
.demand-work-action {
  color: var(--dj-tone);
  border-color: var(--dj-tone-border);
  background: var(--dj-tone-soft);
}
.demand-work-action:enabled:hover,
.demand-work-action[aria-pressed='true'] {
  border-color: var(--dj-tone);
  background: color-mix(in srgb, var(--dj-tone-soft) 90%, var(--dj-tone));
}
.demand-work-action:focus-visible {
  outline: 2px solid var(--dj-tone);
  outline-offset: 3px;
}
</style>
