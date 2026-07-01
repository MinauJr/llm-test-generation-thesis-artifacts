BASE_PROMPT=$1
LANG=$2
FRAMEWORK=$3
SUT=$4

cp $BASE_PROMPT prompt1.txt

sed -i "s/{LANG}/$LANG/g" prompt1.txt
sed -i "s/{FRAMEWORK}/$FRAMEWORK/g" prompt1.txt
sed -i -e "/{UNDER_TEST_SNIPPET}/r $SUT" -e 's/{UNDER_TEST_SNIPPET}//' prompt1.txt


