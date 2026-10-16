<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import Dialog from '@/volt/Dialog.vue'
import InputText from '@/volt/InputText.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { attendanceApi } from '../attendanceApi'
import type { AttendanceLookupFailure, AttendanceRegistered } from '../types'

const props = defineProps<{ eventId: number; eventName: string; listId: number; listName: string }>()
const emit = defineEmits<{ registered: [result: AttendanceRegistered]; closed: [] }>()
const visible = ref(true)
const registration = ref('')
const feedback = ref<'ready' | 'success' | 'duplicate' | 'incomplete' | 'invalid' | 'error'>('ready')
const message = ref('')
const blocked = ref(false)
const focused = ref(false)
const settling = ref(false)
const readingDelay = 300
let readingTimer: ReturnType<typeof setTimeout> | undefined
let feedbackTimer: ReturnType<typeof setTimeout> | undefined
const lookupMessages: Record<AttendanceLookupFailure, string> = {
  not_found: 'Leitura não reconhecida. Mantenha o crachá encostado e tente novamente. Esta leitura não foi registrada.',
  unavailable: 'Não foi possível consultar os participantes agora. Esta leitura não foi registrada. Tente novamente ou chame o responsável.',
  ambiguous: 'Não foi possível identificar uma única pessoa. Esta leitura não foi registrada. Tente novamente ou chame o responsável.',
  unsupported_badge: 'Leitura inválida. Mantenha o crachá encostado e tente novamente. Esta leitura não foi registrada.',
}
const { mutateAsync: register, isPending } = useMutation({
  mutationFn: (value: string) => attendanceApi.register(props.eventId, props.listId, value),
  retry: false,
})
const confirming = computed(() => settling.value || isPending.value)
const tone = computed(() => confirming.value || feedback.value === 'ready' || feedback.value === 'incomplete' ? 'brand'
  : feedback.value === 'success' || feedback.value === 'duplicate' ? 'success' : 'danger')
const icon = computed(() => confirming.value ? 'pi pi-spin pi-spinner'
  : feedback.value === 'success' ? 'pi pi-check'
  : feedback.value === 'duplicate' ? 'pi pi-check-circle'
  : feedback.value === 'incomplete' ? 'pi pi-info-circle'
  : blocked.value ? 'pi pi-exclamation-triangle'
  : feedback.value === 'ready' ? 'pi pi-id-card' : 'pi pi-refresh')
const heading = computed(() => confirming.value ? 'Confirmando presença…'
  : feedback.value === 'success' ? 'Presença confirmada!'
  : feedback.value === 'duplicate' ? 'Sua presença já está registrada'
  : feedback.value === 'incomplete' ? 'Presença registrada'
  : feedback.value === 'invalid' ? 'Tente novamente'
  : feedback.value === 'error' ? blocked.value ? 'Solicite ajuda ao responsável' : 'Não foi possível confirmar'
  : 'Encoste o crachá até receber a aprovação')

async function focusInput() {
  await nextTick()
  if (visible.value && !blocked.value) document.getElementById('attendance-reader-input')?.focus()
}

onMounted(() => window.addEventListener('focus', focusInput))
onBeforeUnmount(() => {
  window.removeEventListener('focus', focusInput)
  cancelReading()
  clearTimeout(feedbackTimer)
})

watch(registration, value => {
  cancelReading()
  if (!value) {
    if (!isPending.value) message.value = ''
    return
  }
  if (!isPending.value && !blocked.value && visible.value) {
    clearTimeout(feedbackTimer)
    feedback.value = 'ready'
    scheduleReading()
  }
}, { flush: 'sync' })

function cancelReading() {
  clearTimeout(readingTimer)
  readingTimer = undefined
  settling.value = false
}

function scheduleReading() {
  if (isPending.value || blocked.value || !visible.value || !registration.value) return
  settling.value = true
  message.value = 'Mantenha o crachá encostado enquanto a leitura é conferida.'
  readingTimer = setTimeout(() => {
    readingTimer = undefined
    settling.value = false
    void confirmReading()
  }, readingDelay)
}

function finishReading() {
  // Enter não antecipa a espera nem reinicia a contagem; Enter vazio/tardio é ignorado.
  if (readingTimer === undefined) scheduleReading()
}

function blurInput() {
  focused.value = false
  cancelReading()
  registration.value = ''
}

function lookupFailure(error: unknown): AttendanceLookupFailure | undefined {
  if (!(error instanceof ApiError) || ![422, 503].includes(error.status)
    || typeof error.detail !== 'object' || error.detail === null) return
  const status = (error.detail as { lookup_status?: unknown }).lookup_status
  if (status === 'not_found' || status === 'unavailable' || status === 'ambiguous' || status === 'unsupported_badge') return status
}

async function confirmReading() {
  if (isPending.value || blocked.value || !visible.value || !registration.value) return
  const value = registration.value
  registration.value = ''
  clearTimeout(feedbackTimer)
  if (!/^[0-9]{12}$/.test(value)) {
    feedback.value = 'invalid'
    message.value = 'Mantenha o crachá encostado no leitor até receber a confirmação.'
    await focusInput()
    return
  }
  message.value = 'Aguarde a confirmação antes de retirar o crachá.'
  try {
    const result = await register(value)
    if (result.lookup_status === 'complete') {
      feedback.value = result.created ? 'success' : 'duplicate'
      message.value = result.created ? `${result.item.name}, sua presença está confirmada. Pode retirar o crachá.`
        : 'Tudo certo. Você já está nesta lista.'
    } else {
      feedback.value = 'incomplete'
      message.value = 'Sua presença foi salva. Alguns dados do cadastro ainda não estão disponíveis.'
    }
    emit('registered', result)
    feedbackTimer = setTimeout(() => {
      feedback.value = 'ready'
      message.value = ''
    }, 3500)
  } catch (error) {
    blocked.value = error instanceof ApiError && [400, 401, 403, 404].includes(error.status)
    const failure = lookupFailure(error)
    feedback.value = failure && failure !== 'unavailable' ? 'invalid' : 'error'
    message.value = failure ? lookupMessages[failure]
      : blocked.value ? 'É necessário conferir a sessão ou esta lista. Chame o responsável pelo evento.'
      : 'Não recebemos a confirmação do servidor. Encoste o crachá novamente para conferir sua presença.'
  }
  // Nunca manter partes de uma próxima leitura que chegaram durante a gravação.
  registration.value = ''
  await focusInput()
}

function closeReader() {
  if (!isPending.value) {
    cancelReading()
    clearTimeout(feedbackTimer)
    registration.value = ''
    visible.value = false
  }
}
</script>

<template>
  <Dialog id="attendance-reader" :visible="visible" modal maximized :draggable="false" :closable="false"
    :close-on-escape="false" :dismissable-mask="false" aria-labelledby="attendance-reader-title"
    :style="{ width: '100vw', height: '100dvh', maxWidth: '100vw', maxHeight: '100dvh', margin: 0 }"
    :class="'dj-tone-' + tone" pt:root:class="rounded-none border-0 bg-dj-canvas"
    pt:header:class="border-b border-dj-border bg-dj-surface px-5 py-4 sm:px-8"
    pt:content:class="flex flex-1 flex-col px-5 py-8 sm:px-8"
    @show="focusInput" @after-hide="emit('closed')">
    <template #header>
      <div class="flex w-full flex-wrap items-center justify-between gap-4">
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold tracking-widest text-dj-brand uppercase">Digital JOST · Presença</p>
          <p class="mt-1 break-words text-sm font-semibold text-dj-ink">{{ eventName }} <span class="font-normal text-dj-muted">/ {{ listName }}</span></p>
        </div>
        <SecondaryButton type="button" label="Encerrar leitura" icon="pi pi-times" outlined :disabled="isPending"
          pt:root:class="rounded-xl" @click="closeReader" />
      </div>
    </template>
    <div class="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center text-center">
      <div class="rounded-3xl border border-dj-border bg-dj-surface px-5 py-10 shadow-dj-card sm:px-10 sm:py-14"
        :aria-busy="confirming" @click.self="focusInput">
        <span class="mx-auto mb-7 flex size-24 items-center justify-center rounded-3xl bg-(--dj-tone-soft) text-(--dj-tone) transition-colors motion-reduce:transition-none" aria-hidden="true">
          <i :class="icon" class="text-5xl" />
        </span>
        <div role="status" aria-live="polite" aria-atomic="true">
          <h2 id="attendance-reader-title" class="text-2xl leading-tight font-bold tracking-tight text-dj-ink sm:text-4xl">{{ heading }}</h2>
          <p class="mx-auto mt-4 max-w-xl text-base leading-7 text-dj-muted">{{ message || 'Aproxime seu crachá e mantenha-o no leitor. A confirmação aparecerá aqui.' }}</p>
        </div>
        <form class="mx-auto mt-8 max-w-sm" novalidate @submit.prevent="finishReading">
          <label for="attendance-reader-input" class="mb-2 block text-xs font-semibold tracking-wide text-dj-muted uppercase">Leitura do crachá</label>
          <InputText id="attendance-reader-input" v-model="registration" type="text" inputmode="none" autofocus
            autocomplete="off" :spellcheck="false" :readonly="isPending || blocked"
            :aria-invalid="feedback === 'invalid'" aria-describedby="attendance-reader-help"
            placeholder="Aguardando leitura…" pt:root:class="w-full rounded-xl py-4 text-center font-mono text-lg tabular-nums"
            @focus="focused = true" @blur="blurInput" />
          <p id="attendance-reader-help" class="mt-3 text-xs leading-5 text-dj-muted">Aguarde a confirmação antes de retirar o crachá.</p>
        </form>
        <SecondaryButton v-if="!focused && !blocked && !isPending" type="button" label="Ativar campo de leitura"
          icon="pi pi-id-card" outlined class="mt-5" @click="focusInput" />
      </div>
      <p class="mt-6 text-sm text-dj-muted">Uma presença por pessoa nesta lista.</p>
    </div>
  </Dialog>
</template>
