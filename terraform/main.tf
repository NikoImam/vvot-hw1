terraform {
  required_providers {
    yandex = {
        source = "yandex-cloud/yandex"
    }
  }

  required_version = ">= 0.13"
}

provider "yandex" {
  zone      = "ru-central1-d"
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  service_account_key_file = "${var.HOME}/.yc-keys/key.json"
}

resource "yandex_iam_service_account" "sa" {
    name      = "hw1-sa"
}

resource "yandex_resourcemanager_folder_iam_member" "ai_languageModels_user" {
  folder_id = var.folder_id
  role      = "ai.languageModels.user"
  member    = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "ai_vision_user" {
  folder_id = var.folder_id
  role   = "ai.vision.user"
  member = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "kms_keys_encrypterDecrypter" {
  folder_id = var.folder_id
  role   = "kms.keys.encrypterDecrypter"
  member = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "lockbox_payloadViewer" {
  folder_id = var.folder_id
  role   = "lockbox.payloadViewer"
  member = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "storage_editor" {
  folder_id = var.folder_id
  role   = "storage.editor"
  member = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_storage_bucket" "prompts_bucket" {
  bucket = var.bucket_name
}

resource "yandex_storage_object" "classifier_prompt" {
  bucket = yandex_storage_bucket.prompts_bucket.bucket
  key    = var.classifier_prompt_object_key
  source = "../bot/classifier_prompt"
}

resource "yandex_storage_object" "gpt_prompt" {
  bucket = yandex_storage_bucket.prompts_bucket.bucket
  key    = var.gpt_prompt_object_key
  source = "../bot/gpt_prompt"
}

resource "yandex_iam_service_account_api_key" "sa_api_key" {
  service_account_id = yandex_iam_service_account.sa.id
}

resource "yandex_iam_service_account_static_access_key" "sa_static_key" {
  service_account_id = yandex_iam_service_account.sa.id
}


resource "yandex_lockbox_secret" "secret" {
  name = "hw1-secret"
}

resource "yandex_lockbox_secret_version" "secret_version" {
  secret_id = yandex_lockbox_secret.secret.id
  
  entries {
    key = "AI_SA_API_KEY"
    text_value = yandex_iam_service_account_api_key.sa_api_key.secret_key
  }

  entries {
    key = "STATIC_KEY"
    text_value = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
  }

  entries {
    key = "STATIC_KEY_ID"
    text_value = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  }

  entries {
    key = "TG_BOT_TOKEN"
    text_value = var.tg_bot_key
  }
}

data "archive_file" "bot_zip" {
  type        = "zip"
  output_path = "./bot.zip"

  source {
    content = file("../bot/main.py")
    filename = "index.py"
  }
  
  source {
    content = file("../bot/requirements.txt")
    filename = "requirements.txt"
  }
}

resource "yandex_function" "bot_function" {
  depends_on = [
      yandex_resourcemanager_folder_iam_member.lockbox_payloadViewer,
      yandex_resourcemanager_folder_iam_member.kms_keys_encrypterDecrypter
    ]

  name = "hw1-vvot05-bot"
  runtime = "python312"
  entrypoint = "index.handler"
  memory = "512"
  execution_timeout = "20"
  service_account_id = yandex_iam_service_account.sa.id
  user_hash = "james-bond"

  content {
    zip_filename = data.archive_file.bot_zip.output_path
  }

  environment = {
    CONFIDENCE_LEVEL = var.confidence_level
    AI_MODEL = var.ai_model
    FOLDER_ID = var.folder_id
    BUCKET_NAME = var.bucket_name
    CLASSIFIER_PROMPT_KEY = var.classifier_prompt_object_key
    GPT_PROMPT_KEY = var.gpt_prompt_object_key
  }

  secrets {
    id = yandex_lockbox_secret.secret.id
    version_id = yandex_lockbox_secret_version.secret_version.id
    key = "AI_SA_API_KEY"
    environment_variable = "AI_SA_API_KEY"
  }

  secrets {
    id = yandex_lockbox_secret.secret.id
    version_id = yandex_lockbox_secret_version.secret_version.id
    key = "STATIC_KEY"
    environment_variable = "STATIC_KEY"
  }

  secrets {
    id = yandex_lockbox_secret.secret.id
    version_id = yandex_lockbox_secret_version.secret_version.id
    key = "STATIC_KEY_ID"
    environment_variable = "STATIC_KEY_ID"
  }

  secrets {
    id = yandex_lockbox_secret.secret.id
    version_id = yandex_lockbox_secret_version.secret_version.id
    key = "TG_BOT_TOKEN"
    environment_variable = "TG_BOT_TOKEN"
  }
}

resource "yandex_function_iam_binding" "bot_function_access" {
  function_id = yandex_function.bot_function.id
  role = "serverless.functions.invoker"

  members = [
    "system:allUsers",
  ]
}

resource "null_resource" "set_webhook" {
  depends_on = [ yandex_function.bot_function ]

  provisioner "local-exec" {
    command = "curl -X POST \"https://api.telegram.org/bot${var.tg_bot_key}/setWebhook?url=https://functions.yandexcloud.net/${yandex_function.bot_function.id}\""
  }
}

resource "null_resource" "delete_webhook" {
  triggers = {
    bot_token = var.tg_bot_key
  }

  provisioner "local-exec" {
    when = destroy
    command = "curl -X POST \"https://api.telegram.org/bot${self.triggers.bot_token}/deleteWebhook\""
  }
}