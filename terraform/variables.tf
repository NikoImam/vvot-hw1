variable "cloud_id" {
    type = string
}

variable "folder_id" {
    type = string
}

variable "HOME" {
    type = string
}

variable "tg_bot_key" {
    type = string
}

variable "bucket_name" {
    type = string
    default = "hw1-vvot05-bucket"
}

variable "classifier_prompt_object_key" {
    type = string
    default = "classifier prompt"
}

variable "gpt_prompt_object_key" {
    type = string
    default = "gpt prompt"
}

variable "confidence_level" {
    type = string
    default = "0.8"
}

variable "ai_model" {
    type = string
    default = "yandexgpt-lite"
}