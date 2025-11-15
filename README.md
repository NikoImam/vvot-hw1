<h1> Домашняя работа №1 | Имамов Нияз Флурович | 11-207 | vvot05 </h1>

## Настройка окружения

```shell
export TF_VAR_cloud_id=<cloud id>
export TF_VAR_folder_id=<folder id>
export TF_VAR_tg_bot_token=<tg-bot token>
export TF_VAR_HOME=$HOME

yc iam service-account create --name hw1-tf-sa

export TERR_SA_ID=$(yc iam service-account get hw1-tf-sa --format json | jq -r .id)

yc resource-manager folder add-access-binding $TF_VAR_folder_id \
    --role admin \
    --subject serviceAccount:$TERR_SA_ID


mkdir -p ~/.yc-keys

yc iam key create --output ~/.yc-keys/key.json --service-account-id $TERR_SA_ID
```

## Развёртывание
```shell
terraform init
```
```shell
terraform apply
```
```shell
terraform destroy
```
```shell
yc iam service-account delete hw1-tf-sa
```