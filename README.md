# vvot-hw1 | Imamov Niyaz | 11-207
Telegram bot for giving exam questions solutions using YandexGPT, Yandex Cloud and Terraform

# Настройка окружения

```shell
yc iam service-account create --name hw1-tf-sa
export TERR_SA_ID=$(yc iam service-account get hw1-tf-sa --format json | jq -r .id)
yc resource-manager folder add-access-binding $FOLDER_ID \
    --role admin \
    --subject serviceAccount:$TERR_SA_ID

export YC_TOKEN=$(yc iam create-token --impersonate-service-account-id $TERR_SA_ID)
export CLOUD_ID=<cloud_id>
export FOLDER_ID=<folder_id>

export TF_VAR_cloud_id=$CLOUD_ID
export TF_VAR_folder_id=$FOLDER_ID
export TF_VAR_yc_sa_iam_key=$YC_TOKEN
```