<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import Textarea from '@/volt/Textarea.vue'
import type { EventCreate } from '../types'

const props = defineProps<{
  busy: boolean
  serverError: string
  fieldErrors: Record<keyof EventCreate, string>
}>()
const emit = defineEmits<{
  submit: [payload: EventCreate]
  cancel: []
}>()
const fields = reactive({ name: '', description: '' })
const errors = reactive({ name: '', description: '' })
const formElement = ref<HTMLFormElement | null>(null)
const nameError = computed(() => errors.name || props.fieldErrors.name)
const descriptionError = computed(() => errors.description || props.fieldErrors.description)

function submit() {
  if (props.busy) return
  const payload = {
    name: fields.name.trim(),
    description: fields.description.trim(),
  }
  errors.name = payload.name.length < 3 || payload.name.length > 120
    ? 'Informe um nome entre 3 e 120 caracteres.' : ''
  errors.description = payload.description.length < 1 || payload.description.length > 2000
    ? 'Informe uma descrição entre 1 e 2.000 caracteres.' : ''
  if (errors.name || errors.description) {
    const invalidId = errors.name ? 'event-name' : 'event-description'
    formElement.value?.querySelector<HTMLElement>('#' + invalidId)?.focus()
    return
  }
  emit('submit', payload)
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="busy" @submit.prevent="submit">
    <p id="event-form-help" class="text-sm text-dj-muted">
      Comece pelo nome e pela descrição do evento.
    </p>

    <div class="mt-6">
      <label for="event-name" class="mb-2 block text-sm font-medium">Nome</label>
      <InputText id="event-name" v-model="fields.name" class="w-full"
        autofocus required :maxlength="120" :invalid="Boolean(nameError)" :disabled="busy"
        :aria-invalid="Boolean(nameError)"
        :aria-describedby="nameError ? 'event-name-error' : undefined" />
      <Message v-if="nameError" id="event-name-error" severity="error" variant="simple"
        size="small" class="mt-2">{{ nameError }}</Message>
    </div>

    <div class="mt-4">
      <label for="event-description" class="mb-2 block text-sm font-medium">Descrição</label>
      <Textarea id="event-description" v-model="fields.description" :rows="4" auto-resize
        required :maxlength="2000" :invalid="Boolean(descriptionError)" :disabled="busy"
        :aria-invalid="Boolean(descriptionError)"
        :aria-describedby="descriptionError ? 'event-description-error' : undefined"
        class="w-full" />
      <Message v-if="descriptionError" id="event-description-error" severity="error"
        variant="simple" size="small" class="mt-2">{{ descriptionError }}</Message>
    </div>

    <Message v-if="serverError" severity="error" class="mt-4">
      {{ serverError }}
    </Message>
    <div class="mt-6 flex flex-wrap gap-3">
      <Button type="submit" :label="busy ? 'Salvando…' : 'Criar evento'"
        :loading="busy" :disabled="busy" />
      <Button type="button" label="Cancelar" outlined :disabled="busy" @click="emit('cancel')" />
    </div>
  </form>
</template>
